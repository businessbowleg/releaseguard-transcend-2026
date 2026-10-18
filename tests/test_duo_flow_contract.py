"""Static boundary tests for candidate Duo v1 flow.

YAML tests cannot substitute for a real GitLab Duo session. They make the
approved-only write boundary and exact tool configuration reviewable.
"""
from pathlib import Path
import unittest

import yaml

ROOT=Path(__file__).resolve().parents[1]
FLOW=ROOT/".gitlab/duo/flows/releaseguard.flow.yml"


class DuoFlowContractTests(unittest.TestCase):
    def setUp(self):
        self.doc=yaml.safe_load(FLOW.read_text(encoding="utf-8"))
        self.nodes={node["name"]:node for node in self.doc["components"]}
        self.routers={r["from"]:r for r in self.doc["routers"]}

    def test_valid_v1_ambient(self):
        self.assertEqual(self.doc["version"],"v1")
        self.assertEqual(self.doc["environment"],"ambient")
        self.assertEqual(self.doc["coding_environment"],"full")
        self.assertEqual(self.doc["flow"]["entry_point"],"investigator")

    def test_investigators_have_read_only_tools(self):
        read_tools={"get_merge_request","get_repository_file","list_repository_tree"}
        for node_name in ("investigator","independent_assessor"):
            self.assertTrue(set(self.nodes[node_name]["toolset"])<=read_tools)

    def test_writer_only_one_approved_note_tool(self):
        writer=self.nodes["approved_audit_publisher"]
        self.assertEqual(writer["type"],"AgentComponent")
        self.assertEqual(set(writer["toolset"]),{
            "get_merge_request","gitlab_api_get","create_merge_request_note"
        })
        self.assertEqual(sum("create_" in item for item in writer["toolset"]),1)

    def test_owner_gate_precedes_writer(self):
        self.assertEqual(self.routers["independent_assessor"]["to"],"owner_gate")
        routes=self.routers["owner_gate"]["condition"]["routes"]
        self.assertEqual(routes["approve"],"approved_audit_publisher")
        self.assertEqual(routes["reject"],"end")
        self.assertEqual(routes["modify"],"independent_assessor")
        self.assertEqual(routes["default_route"],"end")
        self.assertEqual(self.routers["approved_audit_publisher"]["to"],"end")

    def test_owner_gate_can_modify_prior_completed_assessor(self):
        gate=self.nodes["owner_gate"]
        self.assertEqual(gate["type"],"HumanInputComponent")
        self.assertEqual(gate["sends_response_to"],"independent_assessor")
        self.assertEqual(gate["interaction_type"],"approval")
        self.assertIn("on_user_input_prompt",gate["ui_log_events"])
        self.assertIn("on_user_response",gate["ui_log_events"])

    def test_writer_receives_exact_context(self):
        inputs={x["as"]:x["from"] for x in self.nodes["approved_audit_publisher"]["inputs"]}
        self.assertEqual(inputs,{
            "project_id":"context:project_id",
            "merge_request_goal":"context:goal",
            "review_summary":"context:independent_assessor.final_answer",
            "owner_approval":"context:owner_gate.approval",
        })

    def test_prompts_have_completion_and_no_model_override(self):
        self.assertEqual(len(self.doc["prompts"]),3)
        for prompt in self.doc["prompts"]:
            self.assertEqual(prompt["unit_primitives"],[])
            self.assertEqual(prompt["prompt_template"]["placeholder"],"history")
            self.assertNotIn("model",prompt)
            self.assertIn("timeout",prompt["params"])

    def test_publisher_prompt_forbids_prod_and_duplicate_writes(self):
        prompt=next(p for p in self.doc["prompts"] if p["prompt_id"]=="publisher_prompt")
        statement=prompt["prompt_template"]["system"]
        for phrase in ("create_merge_request_note","gitlab_api_get","exactly ONCE",
                       "duplicate","cannot merge","prohibit production promotion",
                       "NO_ACTION"):
            self.assertIn(phrase,statement)

    def test_no_other_write_tools_or_deploy(self):
        all_tools=[tool for node in self.doc["components"] for tool in node.get("toolset",[])]
        for unsafe in ("run_command","create_commit","merge_merge_request","create_file",
                       "edit_file","trigger_pipeline","deploy","create_branch"):
            self.assertNotIn(unsafe,all_tools)

    def test_yaml_cannot_claim_execution(self):
        raw=FLOW.read_text()
        self.assertIn("CANDIDATE",raw)
        self.assertIn("Requires real GitLab",raw)


if __name__=="__main__":
    unittest.main()
