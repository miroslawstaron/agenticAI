from agenticai.examples import seed
from agenticai.models import Agent, Link, Network
from agenticai.store import Store


def legacy_network():
    return Network(
        id="designer-programmer",
        name="Designer & programmer",
        description="A design passed to a C programmer.",
        agents=[
            Agent(
                id="designer",
                name="Designer",
                role="Design a concise solution.",
                x=60,
                y=130,
            ),
            Agent(
                id="programmer",
                name="Programmer",
                role="You are a C programmer. Return a complete C program in a fenced code block.",
                tools=["compiler", "analyzer"],
                x=390,
                y=130,
            ),
        ],
        links=[Link(source="designer", target="programmer")],
        entry_agents=["designer"],
    )


def test_untouched_example_is_upgraded_once(tmp_path):
    store = Store(tmp_path)
    old = legacy_network().model_dump()
    old.pop("initial_task")
    store.put("network", old["id"], old)
    seed(store)
    upgraded = store.get("network", old["id"])
    assert upgraded["name"] == "Programmer & designer"
    assert upgraded["entry_agents"] == ["programmer"]
    assert upgraded["initial_task"]
    assert len(upgraded["links"]) == 2
    seed(store)
    assert store.get("network", old["id"]) == upgraded
    store.close()


def test_edited_example_keeps_user_configuration(tmp_path):
    store = Store(tmp_path)
    edited = legacy_network()
    edited.agents[0].model = "my-model"
    edited.initial_task = "My custom task"
    store.put("network", edited.id, edited)
    seed(store)
    assert store.get("network", edited.id) == edited.model_dump()
    store.close()
