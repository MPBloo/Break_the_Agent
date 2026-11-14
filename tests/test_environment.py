"""Rules, determinism and plumbing. Run with:  python -m unittest discover -s tests -v"""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents import reference  # noqa: E402
from agents.llm_agent import LLMConfig, make_agent  # noqa: E402
from bomber import Episode  # noqa: E402
from bomber.episode import TOOLS  # noqa: E402
from bomber.runner import replay, run_episode  # noqa: E402

HYP = dict(drag=0.035, wind_speed=8, wind_dir=90, shear=0.2, veer=0, updraft=5)
DROP = dict(heading=0, altitude=90, speed=60, x=-400, y=-120)


class Rules(unittest.TestCase):
    def test_same_seed_same_world_and_observations(self):
        a, b = Episode(7), Episode(7)
        self.assertEqual(a.call_tool("test_drop", DROP), b.call_tool("test_drop", DROP))
        self.assertEqual(a.call_tool("begin_operation"), b.call_tool("begin_operation"))
        self.assertNotEqual(Episode(8).call_tool("test_drop", DROP), Episode(7).call_tool("test_drop", DROP))

    def test_reference_is_deterministic(self):
        self.assertEqual(run_episode(reference.run, 2)["score"], run_episode(reference.run, 2)["score"])

    def test_phases(self):
        e = Episode(1)
        self.assertIn("error", e.call_tool("drop", {"target": 1, **DROP}))          # before operation
        self.assertIn("error", e.call_tool("compare", HYP))                          # nothing to compare with
        self.assertNotIn("error", e.call_tool("test_drop", DROP))
        self.assertNotIn("error", e.call_tool("begin_operation"))
        self.assertIn("error", e.call_tool("test_drop", DROP))                       # calibration is over
        self.assertIn("error", e.call_tool("begin_operation"))                       # irreversible
        self.assertNotIn("error", e.call_tool("declare_done"))
        for tool in ("get_mission", "simulate", "compare", "drop", "test_drop", "declare_done"):
            self.assertIn("error", e.call_tool(tool, {}))                            # mission over

    def test_budgets_are_enforced_and_errors_are_free(self):
        e = Episode(1)
        n = e.cfg.n_test_drops
        for _ in range(n):
            self.assertNotIn("error", e.call_tool("test_drop", DROP))
        self.assertIn("error", e.call_tool("test_drop", DROP))
        self.assertIn("error", e.call_tool("compare", {**HYP, "drag": 99}))          # invalid: not charged
        self.assertEqual(e.calcs_used, 0)
        for _ in range(e.cfg.n_calculations):
            self.assertNotIn("error", e.call_tool("compare", HYP))
        self.assertIn("error", e.call_tool("compare", HYP))
        self.assertIn("error", e.call_tool("simulate", {**HYP, **DROP}))

    def test_one_drop_per_target_inside_its_window(self):
        e = Episode(1)
        tg = e.call_tool("begin_operation")["targets"][0]
        ok = dict(target=tg["id"], x=tg["x"], y=tg["y"], heading=tg["heading_range"][0],
                  altitude=tg["altitude_range"][0], speed=tg["speed_range"][0])
        self.assertIn("error", e.call_tool("drop", {**ok, "altitude": tg["altitude_range"][1] + 1 if tg["altitude_range"][1] < 149 else tg["altitude_range"][0] - 1}))
        self.assertNotIn("error", e.call_tool("drop", ok))
        self.assertIn("error", e.call_tool("drop", ok))

    def test_simulate_is_the_real_physics(self):
        """Nothing is hidden beyond the six numbers: aiming with the true air scores ~1."""
        e = Episode(3)
        truth = e._world.air.as_dict()          # test-only peek at the hidden state
        from bomber.client import LocalClient
        reference.Reference(LocalClient(e)).run_with_hypothesis(truth)
        self.assertGreater(e.score()["score"], 0.97)

    def test_replay_reproduces_score(self):
        rec = run_episode(reference.run, 4)
        self.assertEqual(replay(rec)["score"], rec["score"])


class WeatherVariant(unittest.TestCase):
    """The "weather" variant: the wind changes between calibration and operation."""

    def test_base_variant_is_unchanged(self):
        from bomber.config import WEATHER
        base, weather = Episode(5), Episode(5, WEATHER)
        self.assertEqual(base.call_tool("test_drop", DROP), weather.call_tool("test_drop", DROP))   # same calibration world
        self.assertEqual(base._world.air_op, base._world.air)
        self.assertNotEqual(weather._world.air_op.wind_dir, weather._world.air.wind_dir)
        for k in ("drag", "shear", "veer", "updraft"):
            self.assertEqual(getattr(weather._world.air_op, k), getattr(weather._world.air, k))
        self.assertIn("error", base.call_tool("measure_wind", {"altitude": 90}))                  # no such tool in base

    def test_measure_wind_rules(self):
        from bomber.config import WEATHER
        e = Episode(5, WEATHER)
        self.assertIn("error", e.call_tool("measure_wind", {"altitude": 90}))                     # not before the operation
        op = e.call_tool("begin_operation")
        self.assertIn("weather", op)
        for bad in (10, 500, float("nan"), "90"):
            self.assertIn("error", e.call_tool("measure_wind", {"altitude": bad}))
        for _ in range(WEATHER.n_wind_readings):
            self.assertNotIn("error", e.call_tool("measure_wind", {"altitude": 90}))
        self.assertIn("error", e.call_tool("measure_wind", {"altitude": 90}))                     # budget
        self.assertEqual(e.calcs_used, 0)                                                         # readings are free

    def test_reading_the_new_wind_is_what_scores(self):
        from bomber.config import WEATHER
        from agents import heuristics
        adapt = run_episode(reference.run, 2, cfg=WEATHER)["score"]
        ignore = run_episode(heuristics.ignores_weather, 2, cfg=WEATHER)["score"]
        self.assertGreater(adapt, 0.6)
        self.assertLess(ignore, 0.1)

    def test_replay_uses_the_recorded_variant(self):
        from bomber.config import WEATHER
        rec = run_episode(reference.run, 3, cfg=WEATHER)
        self.assertEqual(rec["variant"], "weather")
        self.assertEqual(replay(rec)["score"], rec["score"])


class Plumbing(unittest.TestCase):
    def test_mcp_server_exposes_the_same_tools(self):
        try:
            from bomber.mcp_client import McpClient
        except ImportError:
            self.skipTest("mcp package not installed")
        c = McpClient(1)
        try:
            listed = {t["name"]: t["parameters"] for t in c.list_tools()}
            for t in TOOLS:
                self.assertEqual(sorted(listed[t["name"]].get("properties", {})), sorted(t["parameters"]["properties"]))
                self.assertEqual(sorted(listed[t["name"]].get("required", [])), sorted(t["parameters"]["required"]))
            self.assertEqual(c.call("test_drop", **DROP), Episode(1).call_tool("test_drop", DROP))
        finally:
            c.close()

    def test_llm_loop_against_mock_endpoint(self):
        from tests import mock_llm
        os.environ["NO_PROXY"] = os.environ["no_proxy"] = "127.0.0.1"
        srv, url = mock_llm.start()
        try:
            rec = run_episode(make_agent(LLMConfig(model="mock", base_url=url, api_key="x")), 1)
        finally:
            srv.shutdown()
            srv.server_close()
        self.assertIsNone(rec["agent_error"])
        self.assertEqual(rec["agent_extra"]["stopped"], "done")
        self.assertEqual([e["tool"] for e in rec["log"]],
                         ["get_mission", "test_drop", "compare", "begin_operation", "drop", "declare_done"])
        json.dumps(rec)   # the record is serialisable

    def test_claude_loop_against_mock_endpoint(self):
        try:
            from agents.anthropic_agent import ClaudeConfig, make_agent as make_claude
        except ImportError:
            self.skipTest("anthropic package not installed")
        from tests import mock_anthropic
        os.environ["NO_PROXY"] = os.environ["no_proxy"] = "127.0.0.1"
        srv, url = mock_anthropic.start()
        try:
            rec = run_episode(make_claude(ClaudeConfig(base_url=url, api_key="x")), 1)
        finally:
            srv.shutdown()
            srv.server_close()
        self.assertIsNone(rec["agent_error"])
        self.assertEqual(rec["agent_extra"]["stopped"], "done")
        self.assertEqual([e["tool"] for e in rec["log"]],
                         ["get_mission", "test_drop", "test_drop", "compare", "begin_operation", "declare_done"])
        last = mock_anthropic.SEEN[-1]["body"]
        second_turn = [m for m in last["messages"] if m["role"] == "assistant"][1]
        self.assertEqual(second_turn["content"][0]["signature"], "sig1")       # thinking block echoed untouched
        self.assertEqual([c["type"] for c in last["messages"][4]["content"]], ["tool_result", "tool_result"])
        json.dumps(rec)

    def test_env_file_loader(self):
        import tempfile
        from bomber.envfile import load_env
        with tempfile.NamedTemporaryFile("w", suffix=".env", delete=False) as f:
            f.write("# comment\nBOMBER_TEST_A=one\nexport BOMBER_TEST_B=\"two words\"\nBOMBER_TEST_EMPTY=\nPATH=/nope\n")
        try:
            names = load_env(f.name)
            self.assertEqual(sorted(names), ["BOMBER_TEST_A", "BOMBER_TEST_B"])   # empty and already-set are skipped
            self.assertEqual(os.environ["BOMBER_TEST_B"], "two words")
            self.assertNotEqual(os.environ["PATH"], "/nope")
        finally:
            os.unlink(f.name)
            os.environ.pop("BOMBER_TEST_A", None)
            os.environ.pop("BOMBER_TEST_B", None)


if __name__ == "__main__":
    unittest.main()
