"""Video styles.

The original prompt was hard-coded to one style: a list of surprising facts. That
works, but it is the only shape the generator can produce, so every video from the
project sounds the same.

These thirty styles are the formats that actually carry short-form video. Each one
is a genuinely different narrative shape rather than a change of subject: a
tutorial is not a mystery with different words. Anything obscure was left out
deliberately, because a style nobody searches for is a style nobody watches.

Each entry supplies four things to the prompt:

``description``  what this kind of video is
``structure``    the shape the script must follow
``tone``         how it should sound when read aloud
``hook``         how the opening line should work for this shape
"""

from typing import Dict, List

VIDEO_STYLES: Dict[str, Dict[str, str]] = {
    # ------------------------------------------------------------------
    # Facts and lists
    # ------------------------------------------------------------------
    "facts": {
        "description": "Surprising facts about a subject, delivered rapidly.",
        "structure": (
            "Open with the single strangest fact. Then four to seven more, each one "
            "self-contained and each stranger than the last. No introduction, no "
            "summary at the end."
        ),
        "tone": "Energetic and matter-of-fact. Short sentences. No filler.",
        "hook": "State the most unbelievable fact immediately, with no lead-in.",
    },
    "listicle": {
        "description": "A counted ranking, such as the top five of something.",
        "structure": (
            "Announce what is being counted, then work through the entries in "
            "ascending order of interest so the strongest lands last. Say each "
            "number out loud."
        ),
        "tone": "Punchy and confident. Roughly equal time per entry.",
        "hook": "Promise that one specific entry is the one nobody expects.",
    },
    "countdown": {
        "description": "A ranked countdown from highest number to number one.",
        "structure": (
            "Count downward. Each entry is shorter than the last so the pace "
            "accelerates towards number one, which gets the most time."
        ),
        "tone": "Building tension. Faster as the number falls.",
        "hook": "Name what is being counted down and why number one will surprise them.",
    },
    "myth_busting": {
        "description": "Common beliefs that turn out to be wrong.",
        "structure": (
            "State the belief as most people hold it, then show why it is wrong, "
            "then give what is actually true. Repeat for each myth."
        ),
        "tone": "Confident but not smug. Correct the idea, never the viewer.",
        "hook": "State the myth as if it were true, then immediately deny it.",
    },
    "comparison": {
        "description": "Two things judged against each other.",
        "structure": (
            "Introduce both, then alternate between them on identical criteria. "
            "Hold the verdict back until near the end."
        ),
        "tone": "Even-handed until the verdict, then decisive.",
        "hook": "Name both and promise a winner that surprised you.",
    },

    # ------------------------------------------------------------------
    # Education
    # ------------------------------------------------------------------
    "explainer": {
        "description": "How something works, made clear.",
        "structure": (
            "Ask the question worth asking, build the mechanism one step at a time "
            "with each step resting on the last, then say what it means."
        ),
        "tone": "Clear and patient. Plain words over technical ones.",
        "hook": "Ask the question the viewer cannot answer on their own.",
    },
    "tutorial": {
        "description": "Step-by-step instructions for doing something.",
        "structure": (
            "Show the finished result first, then the numbered steps. Each step "
            "says what to do and why it matters, in that order."
        ),
        "tone": "Direct and practical. Second person: you do this, then this.",
        "hook": "Show the end result, then promise the exact route to it.",
    },
    "science": {
        "description": "A scientific idea or discovery explained.",
        "structure": (
            "Start with the observation that needs explaining, give the evidence, "
            "then the conclusion and what remains unknown."
        ),
        "tone": "Curious and precise. Never overstate what the evidence shows.",
        "hook": "State the observation that should not be possible.",
    },
    "history": {
        "description": "A historical event or period told as a story.",
        "structure": (
            "Set the moment and the stakes, follow what happened in order, end "
            "with the consequence that still matters."
        ),
        "tone": "Narrative and vivid. Present tense for immediacy.",
        "hook": "Drop the viewer into the most dramatic moment first.",
    },
    "technology": {
        "description": "A technology, tool or product explained.",
        "structure": (
            "The problem it solves, how it solves it, what it costs, who it is for."
        ),
        "tone": "Informed and unhyped. Concrete over promotional.",
        "hook": "Name the problem the viewer already recognises.",
    },
    "psychology": {
        "description": "Why people behave the way they do.",
        "structure": (
            "Describe the behaviour so the viewer recognises it in themselves, "
            "explain the mechanism, then what to do about it."
        ),
        "tone": "Insightful and warm. Never diagnostic.",
        "hook": "Describe something the viewer does without knowing why.",
    },
    "finance": {
        "description": "Money, investing or the economy explained.",
        "structure": (
            "The situation, the numbers, what they mean, what a person can do."
        ),
        "tone": "Grounded and specific. Numbers, not vague promises.",
        "hook": "Lead with the number that changes how they see it.",
    },
    "health": {
        "description": "Health, fitness or nutrition, evidence first.",
        "structure": (
            "The claim, what the evidence actually shows, the practical takeaway."
        ),
        "tone": "Careful and honest. Say when evidence is thin.",
        "hook": "State the finding that contradicts common advice.",
    },

    # ------------------------------------------------------------------
    # Story
    # ------------------------------------------------------------------
    "story": {
        "description": "A single narrative with a beginning, a turn and an end.",
        "structure": (
            "Situation, then complication, then consequence. One thread, told in "
            "order. Something must change between the first line and the last."
        ),
        "tone": "Absorbing. Let the events carry the weight.",
        "hook": "Open inside the most striking moment, then explain how it happened.",
    },
    "mystery": {
        "description": "Something unexplained, examined.",
        "structure": (
            "State the anomaly plainly, present the evidence in escalating order, "
            "then the most likely explanation, or admit there is none."
        ),
        "tone": "Measured and eerie. Understatement beats melodrama.",
        "hook": "State the anomaly as plainly and as strangely as possible.",
    },
    "true_crime": {
        "description": "A real case, told responsibly.",
        "structure": (
            "The event, the investigation, the outcome. Stay factual throughout."
        ),
        "tone": (
            "Serious and restrained. Never sensationalise real victims and never "
            "speculate about guilt."
        ),
        "hook": "Open with the detail that made the case unusual.",
    },
    "biography": {
        "description": "One person's life or a decisive part of it.",
        "structure": (
            "The moment that defined them, how they got there, what came of it."
        ),
        "tone": "Human and specific. Details over adjectives.",
        "hook": "Start at their most improbable moment.",
    },
    "disaster": {
        "description": "How something failed, and why.",
        "structure": (
            "The situation before, the chain of failures, the aftermath, the lesson."
        ),
        "tone": "Sober. The facts are dramatic enough without help.",
        "hook": "State the scale of what went wrong in one sentence.",
    },
    "survival": {
        "description": "Someone who survived something extraordinary.",
        "structure": (
            "The ordinary beginning, the moment it turned, the decisions that "
            "mattered, the outcome."
        ),
        "tone": "Tense and immediate. Short sentences under pressure.",
        "hook": "Open at the point of maximum danger.",
    },

    # ------------------------------------------------------------------
    # Nature and space
    # ------------------------------------------------------------------
    "nature": {
        "description": "The natural world, its animals and places.",
        "structure": (
            "Introduce the subject, show what makes it remarkable, place it in its "
            "wider context."
        ),
        "tone": "Wondering and clear. Documentary narration.",
        "hook": "Lead with the most extraordinary thing this creature or place does.",
    },
    "space": {
        "description": "Astronomy, cosmology and spaceflight.",
        "structure": (
            "The object or question, the scale of it, why it matters to us."
        ),
        "tone": "Awed but accurate. Make the scale felt.",
        "hook": "Open with the number or fact that breaks intuition.",
    },
    "ocean": {
        "description": "The sea and what lives in it.",
        "structure": (
            "The depth or place, what survives there, how it manages to."
        ),
        "tone": "Atmospheric and slightly unsettling. The deep is alien.",
        "hook": "Name the depth and what should not be able to live there.",
    },
    "animals": {
        "description": "Animal behaviour and abilities.",
        "structure": (
            "The animal, the ability, how it works, why it evolved."
        ),
        "tone": "Enthusiastic and precise.",
        "hook": "Lead with the ability that sounds invented.",
    },

    # ------------------------------------------------------------------
    # Commentary and opinion
    # ------------------------------------------------------------------
    "opinion": {
        "description": "An argued position on a subject.",
        "structure": (
            "State the position, give the strongest reasons in order, address the "
            "obvious objection, close on the position restated."
        ),
        "tone": "Direct and reasoned. Argue the idea, never the person.",
        "hook": "State the position in its most surprising form.",
    },
    "news": {
        "description": "A recent event explained.",
        "structure": (
            "What happened, why it matters, what happens next."
        ),
        "tone": "Neutral and current. Attribute claims.",
        "hook": "Lead with the development, not the background.",
    },
    "case_study": {
        "description": "One real example examined for what it teaches.",
        "structure": (
            "The situation, what was done, the result, the transferable lesson."
        ),
        "tone": "Analytical and concrete. Real numbers where they exist.",
        "hook": "Open with the result, then explain how it was reached.",
    },
    "mistakes": {
        "description": "Errors people make, and what to do instead.",
        "structure": (
            "Each mistake: name it, show why it is tempting, show the cost, give "
            "the alternative."
        ),
        "tone": "Helpful, never condescending. Assume good intent.",
        "hook": "Name the mistake the viewer is probably making right now.",
    },

    # ------------------------------------------------------------------
    # Entertainment
    # ------------------------------------------------------------------
    "motivational": {
        "description": "Encouragement built on a real idea.",
        "structure": (
            "The obstacle as it feels, the shift in perspective, the concrete "
            "first action."
        ),
        "tone": "Warm and direct. Earned, not shouted.",
        "hook": "Name the feeling the viewer is having right now.",
    },
    "what_if": {
        "description": "A hypothetical followed honestly to its conclusion.",
        "structure": (
            "Pose the scenario, then follow the consequences step by step, each "
            "one grounded in how things actually work."
        ),
        "tone": "Playful but rigorous. Speculation labelled as speculation.",
        "hook": "Pose the scenario in one short sentence.",
    },
    "travel": {
        "description": "A place, what it is like and why it is worth knowing.",
        "structure": (
            "The place, what makes it unlike anywhere else, what it is like to be "
            "there."
        ),
        "tone": "Evocative and sensory. Specific details, not brochure language.",
        "hook": "Open with the detail that makes the place sound impossible.",
    },
}


DEFAULT_STYLE = "facts"


def list_styles() -> List[str]:
    """Every available style name."""
    return sorted(VIDEO_STYLES)


def get_style(name: str) -> Dict[str, str]:
    """Return a style definition, falling back to the original facts style.

    An unknown name is a typo, not a reason to stop, so the default is used and
    the caller is told what happened.
    """
    key = (name or "").strip().lower().replace(" ", "_").replace("-", "_")
    if key in VIDEO_STYLES:
        return VIDEO_STYLES[key]

    if key:
        print(
            f"[Styles] Unknown style '{name}'. Using '{DEFAULT_STYLE}'. "
            f"Available: {', '.join(list_styles())}"
        )
    return VIDEO_STYLES[DEFAULT_STYLE]


def style_exists(name: str) -> bool:
    """True when the name matches a known style."""
    key = (name or "").strip().lower().replace(" ", "_").replace("-", "_")
    return key in VIDEO_STYLES
