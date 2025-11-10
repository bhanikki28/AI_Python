
### Setting up Virtual Env

    python3 -m venv google_adk_demo
    source google_adk_demo/bin/activate


### Install Libraries

    pip3 install google-adk
    pip3 install python-dotenv


###  Get Gemini Key

    https://ai.google.dev/gemini-api/docs

https://www.kaggle.com/code/kaggle5daysofai/day-1b-agent-architectures

### Configure the Agent

    # Summarizer Agent: Its job is to summarize the text it receives.
        summarizer_agent = Agent(
            name="SummarizerAgent",
            model="gemini-2.5-flash-lite",
            # The instruction is modified to request a bulleted list for a clear output format.
            instruction="""Read the provided research findings: {research_findings}
        Create a concise summary as a bulleted list with 3-5 key points.""",
            output_key="final_summary",
        )

    print("✅ summarizer_agent created.")


### Configure the Root Agent

    # Root Coordinator: Orchestrates the workflow by calling the sub-agents as tools.
        root_agent = Agent(
            name="ResearchCoordinator",
            model="gemini-2.5-flash-lite",
            # This instruction tells the root agent HOW to use its tools (which are the other agents).
            instruction="""You are a research coordinator. Your goal is to answer the user's query by orchestrating a workflow.
        1. First, you MUST call the `ResearchAgent` tool to find relevant information on the topic provided by the user.
        2. Next, after receiving the research findings, you MUST call the `SummarizerAgent` tool to create a concise summary.
        3. Finally, present the final summary clearly to the user as your response.""",
            # We wrap the sub-agents in `AgentTool` to make them callable tools for the root agent.
            tools=[
                AgentTool(research_agent),
                AgentTool(summarizer_agent)
            ],
        )

        print("✅ root_agent created.")


### Running the Agent

    runner = InMemoryRunner(agent=root_agent)
    response = await runner.run_debug("What are the latest advancements in quantum computing and what do they mean for AI?")


############################################################################################

## Sequential Agent workflow

## Outline Agent

    # Outline Agent: Creates the initial blog post outline.
    outline_agent = Agent(
        name="OutlineAgent",
        model="gemini-2.5-flash-lite",
        instruction="""Create a blog outline for the given topic with:
        1. A catchy headline
        2. An introduction hook
        3. 3-5 main sections with 2-3 bullet points for each
        4. A concluding thought""",
        output_key="blog_outline", # The result of this agent will be stored in the session state with this key.
    )

    print("✅ outline_agent created.")

##  Writer Agent

    # Writer Agent: Writes the full blog post based on the outline from the previous agent.
    writer_agent = Agent(
        name="WriterAgent",
        model="gemini-2.5-flash-lite",
        # The `{blog_outline}` placeholder automatically injects the state value from the previous agent's output.
        instruction="""Following this outline strictly: {blog_outline}
        Write a brief, 200 to 300-word blog post with an engaging and informative tone.""",
        output_key="blog_draft", # The result of this agent will be stored with this key.
    )

    print("✅ writer_agent created.")

##  Editor Agent

    # Editor Agent: Edits and polishes the draft from the writer agent.
    editor_agent = Agent(
        name="EditorAgent",
        model="gemini-2.5-flash-lite",
        # This agent receives the `{blog_draft}` from the writer agent's output.
        instruction="""Edit this draft: {blog_draft}
        Your task is to polish the text by fixing any grammatical errors, improving the flow and sentence structure, and enhancing overall clarity.""",
        output_key="final_blog", # This is the final output of the entire pipeline.
    )

    print("✅ editor_agent created.")

##  constructing Sequential Agent

    root_agent = SequentialAgent(
        name="BlogPipeline",
        sub_agents=[outline_agent, writer_agent, editor_agent],
    )

    print("✅ Sequential Agent created.") 


##  Agent Runner

    runner = InMemoryRunner(agent=root_agent)
    response = await runner.run_debug("Write a blog post about the benefits of multi-agent systems for software developers")

############################################################################################

## Parallel Agent Workflow

Let's build a system with four agents:

Tech Researcher - Researches AI/ML news and trends
Health Researcher - Researches recent medical news and trends
Finance Researcher - Researches finance and fintech news and trends
Aggregator Agent - Combines all research findings into a single summary

## Tech Researcher Agent

    # Tech Researcher: Focuses on AI and ML trends.
    tech_researcher = Agent(
        name="TechResearcher",
        model="gemini-2.5-flash-lite",
        instruction="""Research the latest AI/ML trends. Include 3 key developments,
    the main companies involved, and the potential impact. Keep the report very concise (100 words).""",
        tools=[google_search],
        output_key="tech_research", # The result of this agent will be stored in the session state with this key.
    )

    print("✅ tech_researcher created.")

## Health Researcher Agent

    # Health Researcher: Focuses on medical breakthroughs.
    health_researcher = Agent(
        name="HealthResearcher",
        model="gemini-2.5-flash-lite",
        instruction="""Research recent medical breakthroughs. Include 3 significant advances,
    their practical applications, and estimated timelines. Keep the report concise (100 words).""",
        tools=[google_search],
        output_key="health_research", # The result will be stored with this key.
    )

    print("✅ health_researcher created.")

## Finance Researcher Agent

    # Finance Researcher: Focuses on fintech trends.
    finance_researcher = Agent(
        name="FinanceResearcher",
        model="gemini-2.5-flash-lite",
        instruction="""Research current fintech trends. Include 3 key trends,
    their market implications, and the future outlook. Keep the report concise (100 words).""",
        tools=[google_search],
        output_key="finance_research", # The result will be stored with this key.
    )

    print("✅ finance_researcher created.")


## Aggregator Agent

    # The AggregatorAgent runs *after* the parallel step to synthesize the results.
    aggregator_agent = Agent(
        name="AggregatorAgent",
        model="gemini-2.5-flash-lite",
        # It uses placeholders to inject the outputs from the parallel agents, which are now in the session state.
        instruction="""Combine these three research findings into a single executive summary:

        **Technology Trends:**
        {tech_research}
        
        **Health Breakthroughs:**
        {health_research}
        
        **Finance Innovations:**
        {finance_research}
        
        Your summary should highlight common themes, surprising connections, and the most important key takeaways from all three reports. The final summary should be around 200 words.""",
        output_key="executive_summary", # This will be the final output of the entire system.
    )

    print("✅ aggregator_agent created.")

## Runner

    # The ParallelAgent runs all its sub-agents simultaneously.
parallel_research_team = ParallelAgent(
    name="ParallelResearchTeam",
    sub_agents=[tech_researcher, health_researcher, finance_researcher],
)

# This SequentialAgent defines the high-level workflow: run the parallel team first, then run the aggregator.
root_agent = SequentialAgent(
    name="ResearchSystem",
    sub_agents=[parallel_research_team, aggregator_agent],
)

print("✅ Parallel and Sequential Agents created.")

runner = InMemoryRunner(agent=root_agent)
response = await runner.run_debug("Run the daily executive briefing on Tech, Health, and Finance")