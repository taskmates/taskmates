from typing import Dict, Callable, Iterable, Tuple, Any

Facts = Dict[str, Any]
Matcher = Callable[[Facts], bool]
Action = Callable[[Facts], Tuple[Any, bool]]  # Return value now includes a boolean to continue execution
Rule = Tuple[Matcher, Action]


class RulesEngine:
    def __init__(self, facts: Facts):
        self.facts = facts
        self.rules = []

    def add_rule(self, matcher: Matcher, action: Action):
        self.rules.append((matcher, action))

    def execute_rules(self):
        for matcher, action in self.rules:
            if matcher(self.facts):
                result, continue_execution = action(self.facts)
                yield result
                if not continue_execution:
                    break

    def update_facts(self, new_facts: Facts):
        self.facts.update(new_facts)


# Pytest tests
import pytest


def test_rules_engine_initialization():
    facts = {"temperature": 25, "humidity": 60}
    engine = RulesEngine(facts)
    assert engine.facts == facts
    assert engine.rules == []


def test_add_rule():
    engine = RulesEngine({})
    matcher = lambda facts: facts.get("temperature", 0) > 30
    action = lambda facts: ("It's hot!", True)
    engine.add_rule(matcher, action)
    assert len(engine.rules) == 1
    assert engine.rules[0] == (matcher, action)


def test_execute_rules():
    facts = {"temperature": 35}
    engine = RulesEngine(facts)

    matcher1 = lambda facts: facts["temperature"] > 30
    action1 = lambda facts: ("It's hot!", True)
    engine.add_rule(matcher1, action1)

    matcher2 = lambda facts: facts["temperature"] > 40
    action2 = lambda facts: ("It's very hot!", True)
    engine.add_rule(matcher2, action2)

    results = list(engine.execute_rules())
    assert results == ["It's hot!"]


def test_update_facts():
    engine = RulesEngine({"temperature": 25})
    engine.update_facts({"humidity": 60})
    assert engine.facts == {"temperature": 25, "humidity": 60}


def test_lazy_execution():
    facts = {"temperature": 35}
    engine = RulesEngine(facts)

    def slow_matcher(facts):
        import time
        time.sleep(0.1)
        return facts["temperature"] > 30

    def slow_action(facts):
        import time
        time.sleep(0.1)
        return "It's hot!", True

    engine.add_rule(slow_matcher, slow_action)

    generator = engine.execute_rules()

    # The generator should be created immediately without executing the rules
    assert isinstance(generator, Iterable)

    # Only when we iterate over the generator, the rules should be executed
    results = list(generator)
    assert results == ["It's hot!"]


def test_short_circuit_execution():
    facts = {"temperature": 35, "humidity": 70}
    engine = RulesEngine(facts)

    matcher1 = lambda facts: facts["temperature"] > 30
    action1 = lambda facts: ("It's hot!", True)
    engine.add_rule(matcher1, action1)

    matcher2 = lambda facts: facts["humidity"] > 60
    action2 = lambda facts: ("It's humid!", False)  # This action will short-circuit the execution
    engine.add_rule(matcher2, action2)

    matcher3 = lambda facts: facts["temperature"] > 40
    action3 = lambda facts: ("It's very hot!", True)
    engine.add_rule(matcher3, action3)

    results = list(engine.execute_rules())
    assert results == ["It's hot!", "It's humid!"]
    # The third rule should not be executed due to short-circuiting


if __name__ == "__main__":
    pytest.main([__file__])
