from .models import Agent, Link, Network, Provider, Tool


def seed(store):
    if not store.get("provider", "demo"):
        store.put("provider", "demo", Provider(id="demo", supports_tools=True))
    builtins = [
        Tool(
            id="compiler",
            name="C compiler",
            kind="compiler",
            description="Compile C code with GCC. Return diagnostics; does not execute the compiled program.",
            input_schema={
                "type": "object",
                "properties": {"code": {"type": "string"}},
                "required": ["code"],
            },
        ),
        Tool(
            id="analyzer",
            name="Static analyzer",
            kind="analyzer",
            description="Analyze C code using cppcheck.",
            input_schema={
                "type": "object",
                "properties": {"code": {"type": "string"}},
                "required": ["code"],
            },
        ),
        Tool(
            id="shell",
            name="Shell",
            kind="shell",
            description="Execute a noninteractive command in the run workspace.",
            input_schema={
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
                "additionalProperties": False,
            },
        ),
        Tool(
            id="python-version",
            name="Python version",
            executable="@python",
            args=["--version"],
            description="Report the Python interpreter version.",
        ),
    ]
    for tool in builtins:
        if not store.get("tool", tool.id):
            store.put("tool", tool.id, tool)
    teacher = Agent(
        id="teacher",
        name="Teacher",
        role="Suggest improvements to the student's solution.",
        x=420,
        y=100,
        max_visits=2,
    )
    student = Agent(
        id="student",
        name="Student",
        role="Solve the task and apply feedback.",
        x=70,
        y=100,
        max_visits=2,
    )
    designer = Agent(
        id="designer",
        name="Designer",
        role="Review the C program against the original task. Suggest concrete design improvements for the programmer to apply.",
        x=390,
        y=130,
        max_visits=3,
    )
    programmer = Agent(
        id="programmer",
        name="Programmer",
        role="You are a C programmer. Return a complete C program in a fenced code block.",
        tools=["compiler", "analyzer"],
        x=60,
        y=130,
        max_visits=3,
    )
    compile_step = Agent(
        id="compile",
        name="Compile",
        kind="tool",
        tool_id="compiler",
        tool_arguments={"code": "${message}"},
        x=710,
        y=40,
    )
    analyze_step = Agent(
        id="analyze",
        name="Analyze",
        kind="tool",
        tool_id="analyzer",
        tool_arguments={"code": "${message}"},
        x=710,
        y=230,
    )
    networks = [
        Network(
            id="teacher-student",
            name="Teacher & student",
            description="Two rounds of solution and feedback.",
            initial_task="Explain how a binary search works and give a small example.",
            agents=[student, teacher],
            links=[
                Link(source="student", target="teacher"),
                Link(source="teacher", target="student"),
            ],
            entry_agents=["student"],
        ),
        Network(
            id="designer-programmer",
            name="Programmer & designer",
            description="Give Programmer a task, review the code with Designer, and apply feedback for three rounds.",
            initial_task="Write a small C program that prints a greeting. Review its design and improve it using the designer's feedback.",
            agents=[programmer, designer],
            links=[
                Link(
                    source="programmer",
                    target="designer",
                    template="Original task:\n{task}\n\nReview this program and suggest improvements:\n{message}",
                ),
                Link(
                    source="designer",
                    target="programmer",
                    template="Improve your program using this design feedback:\n{message}",
                ),
            ],
            entry_agents=["programmer"],
        ),
        Network(
            id="compiler-analyzer",
            name="C verification",
            description="Generate C, then compile and analyze in parallel.",
            initial_task="Write a C program that prints a greeting, then compile and statically analyze it.",
            agents=[programmer, compile_step, analyze_step],
            links=[
                Link(source="programmer", target="compile"),
                Link(source="programmer", target="analyze"),
            ],
            entry_agents=["programmer"],
        ),
        Network(
            id="autonomous-team",
            name="Autonomous team",
            description="A coordinator creates a research assistant and delegates work.",
            initial_task="Delegate research on a small C application, review the findings, and summarize the solution.",
            mode="autonomous",
            agents=[
                Agent(
                    id="coordinator",
                    name="Coordinator",
                    role="Delegate research, review results, and complete the task.",
                    can_orchestrate=True,
                    x=180,
                    y=100,
                )
            ],
            entry_agents=["coordinator"],
        ),
    ]
    # Replace only the untouched built-in from the previous release. A user's
    # edited network keeps its agents, prompts, models, tools and connections.
    legacy = Network(
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
                role=programmer.role,
                tools=["compiler", "analyzer"],
                x=390,
                y=130,
            ),
        ],
        links=[Link(source="designer", target="programmer")],
        entry_agents=["designer"],
    )

    def signature(network):
        data = network.model_dump()
        for link in data["links"]:
            link.pop("id")
        return data

    for network in networks:
        existing = store.get("network", network.id)
        if not existing or (
            network.id == legacy.id
            and signature(Network.model_validate(existing)) == signature(legacy)
        ):
            store.put("network", network.id, network)
        elif "initial_task" not in existing:
            store.put(
                "network",
                network.id,
                {**existing, "initial_task": network.initial_task},
            )
