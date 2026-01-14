from pathlib import Path

FILES_FOLDER=Path('files')

# Paper configuration
PAPER_TITLE = "LACY: Simulating Expert Guidance for Software Onboarding with Code Tours"
PAPER_ABSTRACT = """
Context. Software engineers often need to understand code they
did not originally author—whether during onboarding, collabora-
tion, project handovers, or when working with legacy systems.
Traditional documentation, comments, or design notes are typically
fragmented, outdated, and lack a clear entry point or narrative.
What developers miss is the experience of an expert guiding them
step by step, explaining information flow, design decisions, and
constraints in a canonical and intuitive way.
Objective. We present Lacy, an AI-assisted tool designed to
simulate expert guidance for code documentation and onboard-
ing. Lacy reduces the repetitive burden on experts while helping
developers make sense of large code bases without losing direction.
Methodology. Lacy is implemented as a Visual Studio Code
extension, allowing users to create or follow guided multi-file tours,
take comprehension quizzes, and pose questions to code base ex-
perts of the project. A complementary web-based dashboard enables
these code base experts to monitor learner progress, respond to
queries, and visualize onboarding metrics.
Results.
Conclusions. By bridging the gap between code base experts
and learners, Lacy reduces onboarding times for new hires and
enhances maintainability of code bases, especially in legacy systems.
Our approach introduces a collaborative, structured, and interactive
paradigm for code base learning and dynamic documentation. A
demonstration video of Lacy is available at https://www.youtube.
com/watch?v=TwHs3akSzr8.
""".strip()

# Number of relevant papers to find
NUM_RELEVANT_PAPERS = 200

# Conference website URL
CONFERENCE_WEBSITE = "https://conf.researchr.org/committee/fse-2026/fse-2026-industry-papers-program-committee"