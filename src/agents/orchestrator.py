from typing import Dict, List

from .agent_base import Agent
from .coverage_agent import CoverageAgent

_LOW_CONFIDENCE_RECHECK = True   # set False to disable automatic re-queries


class OrchestratorAgent(Agent):
    """Coordinates coverage analysis across a full SOC 2 checklist.

    Delegates each requirement to CoverageAgent, detects low-confidence
    results and triggers a single re-query with the agent's own suggested
    recheck terms, then assembles a gap report.

    Args:
        coverage_agent: A configured CoverageAgent instance.
    """

    def __init__(self, coverage_agent: CoverageAgent) -> None:
        super().__init__(
            name="OrchestratorAgent",
            role="Coordinate requirement analysis and produce gap report",
            tools=["call_coverage_agent", "write_decision_log"],
        )
        self.coverage_agent = coverage_agent

    def process_message(self, message: Dict) -> Dict:
        """Run coverage analysis for a list of requirements.

        Args:
            message: Dict with key:
                - requirements: List[Dict], each with at minimum
                  "requirement_id", "requirement_text", and optionally
                  "category", "control_objective".

        Returns:
            Gap report dict:
            {
              "covered":  [requirement_ids],
              "partial":  [requirement_ids],
              "at_risk":  [requirement_ids],
              "details":  {requirement_id: assessment_dict}
            }
        """
        requirements: List[Dict] = message.get("requirements", [])
        total = len(requirements)

        self.log_message("start", {"total_requirements": total})
        print(f"\n[Orchestrator] Processing {total} requirement(s)...\n")

        gap_report: Dict = {"covered": [], "partial": [], "at_risk": [], "details": {}}

        for idx, req in enumerate(requirements, 1):
            req_id = req.get("requirement_id", f"REQ_{idx}")
            print(f"  [{idx}/{total}] {req_id} — ", end="", flush=True)

            # --- first pass ---
            self.log_message("delegate", {"requirement_id": req_id, "pass": 1})
            result = self.coverage_agent.process_message(req)

            # --- re-query if confidence is low ---
            if (
                _LOW_CONFIDENCE_RECHECK
                and result.get("confidence") == "low"
                and result.get("suggested_recheck_terms")
            ):
                recheck_terms = result["suggested_recheck_terms"]
                self.log_message(
                    "recheck",
                    {"requirement_id": req_id, "terms": recheck_terms},
                )
                print(f"low confidence, rechecking... ", end="", flush=True)

                recheck_msg = dict(req)
                recheck_msg["recheck_terms"] = recheck_terms
                recheck_result = self.coverage_agent.process_message(recheck_msg)

                # Keep whichever result has higher confidence / better assessment
                _rank = {"Covered": 2, "Partial": 1, "At Risk": 0}
                _conf = {"high": 2, "medium": 1, "low": 0}
                orig_score   = _rank.get(result.get("assessment", ""), 0) + _conf.get(result.get("confidence", ""), 0)
                recheck_score = _rank.get(recheck_result.get("assessment", ""), 0) + _conf.get(recheck_result.get("confidence", ""), 0)
                if recheck_score >= orig_score:
                    result = recheck_result
                    self.log_message("recheck_adopted", {"requirement_id": req_id})

            # --- classify ---
            assessment = result.get("assessment", "At Risk")
            confidence = result.get("confidence", "low")

            bucket = {"Covered": "covered", "Partial": "partial", "At Risk": "at_risk"}.get(
                assessment, "at_risk"
            )
            gap_report[bucket].append(req_id)
            gap_report["details"][req_id] = result

            self.log_message(
                "classified",
                {"requirement_id": req_id, "bucket": bucket, "confidence": confidence},
            )
            print(f"{assessment} ({confidence} confidence)")

        # --- summary ---
        self.log_message("complete", {
            "covered": len(gap_report["covered"]),
            "partial":  len(gap_report["partial"]),
            "at_risk":  len(gap_report["at_risk"]),
        })

        return gap_report
