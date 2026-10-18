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
        self.assertEqual(self.doc["coding_environment"],"none")
        self.assertEqual(self.doc["flow"]["entry_point"],"investigator")

    def test_investigators_have_read_only_tools(self):
        read_tools={"get_merge_request","get_repository_file","list_repository_tree",
                    "list_merge_request_diffs","gitlab_api_get",
                    "get_pipeline_errors","get_job_logs"}
        for node_name in ("investigator","independent_assessor"):
            self.assertTrue(set(self.nodes[node_name]["toolset"])<=read_tools)

    def test_writer_only_one_approved_note_tool(self):
        writer=self.nodes["approved_audit_publisher"]
        self.assertEqual(writer["type"],"AgentComponent")
        self.assertEqual(set(writer["toolset"]),{
            "get_merge_request","list_all_merge_request_notes","create_merge_request_note"
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

    def test_human_gate_must_show_independent_findings(self):
        gate=self.nodes["owner_gate"]
        attrs={x["as"]:x["from"] for x in gate["inputs"]}
        self.assertEqual(attrs,{
            "review_project":"context:project_id",
            "review_mr_iid":"context:goal",
            "review_summary":"context:independent_assessor.final_answer",
        })
        msg=gate["message_template"]
        for slot in ("{{ review_project }}","{{ review_mr_iid }}",
                     "{{ review_summary }}"):
            self.assertIn(slot,msg)
        self.assertIn("ONE public merge-request REVIEW NOTE",msg)
        self.assertIn("Reject or modify",msg)
        self.assertIn("does not authorize merging",msg)

    def test_read_only_api_mode_requires_no_clone(self):
        self.assertEqual(self.doc["coding_environment"],"none")
        used={x for node in self.nodes.values() for x in node.get("toolset",[])}
        self.assertNotIn("run_command",used)
        self.assertNotIn("read_file",used)
        self.assertIn("get_pipeline_errors",used)
        self.assertIn("list_merge_request_diffs",used)
        self.assertIn("gitlab_api_get",used)

    def test_approval_is_only_route_to_writer(self):
        routes=self.doc["routers"]
        paths=[]
        for r in routes:
            if "to" in r and r["to"]=="approved_audit_publisher":
                paths.append(r["from"])
            if "condition" in r:
                paths.extend((r["from"],k) for k,v in
                             r["condition"]["routes"].items()
                             if v=="approved_audit_publisher")
        self.assertEqual(paths,[("owner_gate","approve")])

    def test_assessor_requires_real_ci_identity(self):
        prompt=next(p for p in self.doc["prompts"]
                    if p["prompt_id"]=="assessor_prompt")
        sys=prompt["prompt_template"]["system"]
        for v in ("exact commit","pipeline ID","job status",
                  "UNVERIFIED","local fixture"):
            self.assertIn(v,sys)

    def test_writer_receives_exact_context(self):
        inputs={x["as"]:x["from"] for x in self.nodes["approved_audit_publisher"]["inputs"]}
        self.assertEqual(inputs,{
            "project_id":"context:project_id",
            "mr_iid":"context:goal",
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
        for phrase in ("create_merge_request_note","list_all_merge_request_notes","exactly ONCE",
                       "duplicate","cannot merge","prohibit production promotion",
                       "NO_ACTION"):
            self.assertIn(phrase,statement)

    def test_only_mr_reviewer_trigger_is_supported(self):
        raw=FLOW.read_text()
        self.assertIn("MERGE REQUEST reviewer",raw)
        self.assertIn("not free-form instructions",raw)
        self.assertIn("Do not enable this flow for issue",raw)

    def test_all_agents_use_numeric_trigger_iid(self):
        for name in ("investigator","independent_assessor","approved_audit_publisher"):
            comp=self.nodes[name]
            bindings={a["as"]:a["from"] for a in comp["inputs"]}
            self.assertEqual(bindings["mr_iid"],"context:goal")
            self.assertEqual(bindings["project_id"],"context:project_id")
            prompt=next(p for p in self.doc["prompts"] if p["prompt_id"]==comp["prompt_id"])
            system=prompt["prompt_template"]["system"]
            self.assertIn("decimal",system)
            self.assertIn("project_id",system)
        self.assertIn("numeric",self.doc["prompts"][1]["prompt_template"]["system"])

    def test_gate_displays_exact_mr_and_blocks_ambiguous_target(self):
        msg=self.nodes["owner_gate"]["message_template"]
        self.assertIn("!{{ review_mr_iid }}",msg)
        self.assertIn("malformed or missing IID",msg)
        self.assertIn("REVIEW REQUIRED",msg)

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
