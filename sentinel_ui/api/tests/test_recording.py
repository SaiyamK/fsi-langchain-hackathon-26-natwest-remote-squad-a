"""A Reset or restart in record mode must add to the recording, never wipe it."""

from sentinel_api.investigators import Outcome
from sentinel_api.recording import RecordingInvestigator, load


class Fake:
    def run(self, tx, rule_score, reasons, on_step, ask_human):
        on_step("supervisor", "working")
        return Outcome(record={"transaction_id": tx["transaction_id"], "final_decision": "clear"}, seconds=0.1)


def test_new_session_keeps_earlier_recordings(tmp_path):
    path = tmp_path / "world0.json"
    first = RecordingInvestigator(Fake(), "m", path)
    first.run({"transaction_id": "TX-1"}, 40, [], lambda *a, **k: None, lambda q: {})
    second = RecordingInvestigator(Fake(), "m", path)  # what a Reset creates
    second.run({"transaction_id": "TX-2"}, 40, [], lambda *a, **k: None, lambda q: {})
    assert set(load(path)["investigations"]) == {"TX-1", "TX-2"}
