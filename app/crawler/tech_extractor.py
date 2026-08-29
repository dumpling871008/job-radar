import re


def _compile(pattern, flags=re.IGNORECASE):
    return re.compile(pattern, flags)


TECH_PATTERNS = (
    ("Python", (_compile(r"(?<![\w])python(?![\w])"),)),
    ("Java", (_compile(r"(?<![\w])java(?![\w])"),)),
    (
        "JavaScript",
        (
            _compile(
                r"(?<![\w])(?:javascript|java\s*script|js)(?![\w])"
            ),
        ),
    ),
    (
        "TypeScript",
        (_compile(r"(?<![\w])typescript(?![\w])"),),
    ),
    ("C#", (_compile(r"(?<![\w])c\s*#(?![\w])"),)),
    (
        "C++",
        (_compile(r"(?<![\w])c\s*\+\+(?![\w])"),),
    ),
    (
        "Go",
        (
            _compile(r"(?<![\w])golang(?![\w])"),
            _compile(
                r"(?:熟悉|使用|精通|開發|experience\s+(?:with|in))"
                r"\s*[:：]?\s*Go(?![\w])",
                0,
            ),
            _compile(
                r"(?<![\w])Go(?=\s+(?:language|developer|engineer))",
                0,
            ),
            _compile(
                r"(?:^|[,/、|]\s*)Go(?=\s*(?:[,/、|]|$))",
                re.MULTILINE,
            ),
        ),
    ),
    ("PHP", (_compile(r"(?<![\w])php(?![\w])"),)),
    (
        "FastAPI",
        (_compile(r"(?<![\w])fastapi(?![\w])"),),
    ),
    ("Flask", (_compile(r"(?<![\w])flask(?![\w])"),)),
    ("Django", (_compile(r"(?<![\w])django(?![\w])"),)),
    (
        "Spring Boot",
        (
            _compile(
                r"(?<![\w])spring[ ._-]*boot(?![\w])"
            ),
        ),
    ),
    (
        "Node.js",
        (
            _compile(
                r"(?<![\w])node(?:\.?js)(?![\w])"
            ),
        ),
    ),
    (
        "Express",
        (
            _compile(
                r"(?<![\w])express(?:\.?js)?(?![\w])"
            ),
        ),
    ),
    (
        "React",
        (_compile(r"(?<![\w])react(?:\.?js)?(?![\w])"),),
    ),
    (
        "Vue",
        (_compile(r"(?<![\w])vue(?:\.?js)?(?![\w])"),),
    ),
    (
        "Angular",
        (_compile(r"(?<![\w])angular(?:\.?js)?(?![\w])"),),
    ),
    (
        "Next.js",
        (_compile(r"(?<![\w])next(?:\.?js)(?![\w])"),),
    ),
    (
        "PostgreSQL",
        (
            _compile(
                r"(?<![\w])(?:postgresql|postgres)(?![\w])"
            ),
        ),
    ),
    ("MySQL", (_compile(r"(?<![\w])mysql(?![\w])"),)),
    (
        "MongoDB",
        (_compile(r"(?<![\w])mongodb(?![\w])"),),
    ),
    ("Redis", (_compile(r"(?<![\w])redis(?![\w])"),)),
    ("Oracle", (_compile(r"(?<![\w])oracle(?![\w])"),)),
    ("Docker", (_compile(r"(?<![\w])docker(?![\w])"),)),
    (
        "Kubernetes",
        (
            _compile(
                r"(?<![\w])(?:kubernetes|k8s)(?![\w])"
            ),
        ),
    ),
    ("AWS", (_compile(r"(?<![\w])aws(?![\w])"),)),
    ("GCP", (_compile(r"(?<![\w])gcp(?![\w])"),)),
    ("Azure", (_compile(r"(?<![\w])azure(?![\w])"),)),
    ("Linux", (_compile(r"(?<![\w])linux(?![\w])"),)),
    (
        "Terraform",
        (_compile(r"(?<![\w])terraform(?![\w])"),),
    ),
    (
        "Jenkins",
        (_compile(r"(?<![\w])jenkins(?![\w])"),),
    ),
    (
        "GitHub Actions",
        (
            _compile(
                r"(?<![\w])github\s+actions?(?![\w])"
            ),
        ),
    ),
    ("PyTorch", (_compile(r"(?<![\w])pytorch(?![\w])"),)),
    (
        "TensorFlow",
        (_compile(r"(?<![\w])tensorflow(?![\w])"),),
    ),
    ("YOLO", (_compile(r"(?<![\w])yolo(?![\w])"),)),
    ("LLM", (_compile(r"(?<![\w])llms?(?![\w])"),)),
    ("RAG", (_compile(r"(?<![\w])rag(?![\w])"),)),
    (
        "LangChain",
        (_compile(r"(?<![\w])langchain(?![\w])"),),
    ),
    (
        "LlamaIndex",
        (_compile(r"(?<![\w])llamaindex(?![\w])"),),
    ),
    ("Pandas", (_compile(r"(?<![\w])pandas(?![\w])"),)),
    ("Spark", (_compile(r"(?<![\w])spark(?![\w])"),)),
    (
        "Airflow",
        (_compile(r"(?<![\w])airflow(?![\w])"),),
    ),
)


def extract_tech_stack(title, description=""):
    """從 title/JD 以 deterministic、邊界感知規則擷取技術。"""

    text = "\n".join(
        part
        for part in (
            title or "",
            description or "",
        )
        if part
    )

    return [
        canonical_name
        for canonical_name, patterns in TECH_PATTERNS
        if any(
            pattern.search(text)
            for pattern in patterns
        )
    ]
