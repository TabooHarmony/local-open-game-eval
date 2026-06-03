"""
skill_router.py — Content-based skill routing for OpenGameEval harness.

Routes eval prompts to the most relevant skills using BM25 scoring
augmented with example utterances (inspired by semantic-router/aurelio-labs).

The utterance layer bridges the gap between natural-language eval prompts
("make cars faster") and technical skill descriptions ("Constraints, VehicleSeat").
"""
import re
import math
from pathlib import Path
from collections import Counter
from typing import Optional


_STOP_WORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "to", "of", "in", "for",
    "on", "with", "at", "by", "from", "as", "into", "through", "during",
    "before", "after", "above", "below", "between", "out", "off", "over",
    "under", "again", "further", "then", "once", "here", "there", "when",
    "where", "why", "how", "all", "both", "each", "few", "more", "most",
    "other", "some", "such", "no", "nor", "not", "only", "own", "same",
    "so", "than", "too", "very", "just", "because", "but", "and", "or",
    "if", "while", "about", "up", "down", "that", "this", "these",
    "those", "it", "its", "i", "me", "my", "we", "our", "you", "your",
    "he", "him", "his", "she", "her", "they", "them", "their", "what",
    "which", "who", "whom", "also", "like", "want", "need", "add",
})

# Example utterances per skill — natural-language phrases that should route
# to each skill. Bridges the gap between eval prompts and technical descriptions.
# Inspired by semantic-router's Route.utterances pattern.
SKILL_UTTERANCES: dict[str, list[str]] = {
    "roblox-physics": [
        "make cars faster", "car speed", "vehicle speed", "racing",
        "friction", "sliding", "drifting", "car physics",
        "gravity", "gravity well", "invert gravity",
        "falling", "cube falls", "object falls",
        "orbital", "orbit", "attract towards player",
        "ragdoll", "projectile", "throw", "launch",
        "constraint", "hinge", "spring", "weld",
        "network ownership", "physics replication",
    ],
    "roblox-building": [
        "change color", "green cube", "red part", "blue part",
        "logo cube", "change the cube", "paint",
        "build", "construct", "create part",
        "traffic light", "door", "puzzle",
        "csg", "union", "negate", "mesh",
        "spawn location", "baseplate", "map design",
    ],
    "roblox-animation-vfx": [
        "smoke", "emit smoke", "particle", "particles",
        "fire", "sparkle", "beam", "trail",
        "animate", "animation", "tween",
        "leaves fall", "falling leaves", "autumn",
        "visual effect", "vfx", "explosion",
        "fade", "glow", "highlight",
    ],
    "roblox-gui": [
        "gui", "ui", "screen gui", "button",
        "shop", "purchase", "inventory display",
        "health bar", "score display", "timer",
        "scrolling frame", "layout", "responsive",
        "text label", "image label", "frame",
        "hotbar", "toolbar", "menu",
    ],
    "roblox-npc-ai": [
        "npc", "enemy", "entity that chases", "chase",
        "pathfinding", "follow player", "patrol",
        "state machine", "ai behavior", "npc detection",
        "spawn npc", "enemy ai", "monster",
    ],
    "roblox-lighting": [
        "lighting", "day night cycle", "time of day",
        "atmosphere", "bloom", "fog",
        "post processing", "color correction",
        "sunrise", "sunset", "ambient",
    ],
    "roblox-audio": [
        "music", "play music", "sound", "audio",
        "spatial audio", "3d sound", "volume",
        "sfx", "sound effect", "waterfall sound",
        "trigger sound", "background music",
    ],
    "roblox-data": [
        "datastore", "save", "persist", "inventory save",
        "player data", "session locking",
        "profile store", "update async",
        "leaderstats", "leaderboard",
    ],
    "roblox-economy": [
        "currency", "coins", "gold", "money",
        "shop", "buy", "purchase", "price",
        "game pass", "developer product",
        "faucet", "sink", "economy",
    ],
    "roblox-security": [
        "exploit", "anti cheat", "server authority",
        "validate", "remote event security",
        "rate limit", "sanity check",
    ],
    "roblox-networking": [
        "remote event", "remote function",
        "client server", "replication",
        "networking", "server authoritative",
    ],
    "roblox-performance": [
        "optimize", "lag", "performance", "fps",
        "memory", "mobile", "streaming",
        "object pooling", "microprofiler",
    ],
    "roblox-luau-core": [
        "luau", "lua", "script", "walkspeed",
        "player character", "character height",
        "remove legs", "spawn as r6", "r6 character",
        "hold shift", "sprint", "walkspeed change",
    ],
    "roblox-sharp-edges": [
        "datastore loss", "data loss", "currency exploit",
        "process receipt", "memory leak",
    ],
    "roblox-studio-mcp": [
        "mcp", "tool", "execute luau", "script read",
        "multi edit", "search game tree",
    ],
    "roblox-code-review": [
        "review", "code review", "checklist",
        "best practices", "audit",
    ],
    "roblox-publish-checklist": [
        "publish", "release", "pre publish",
        "checklist", "mobile", "accessibility",
    ],
}


def tokenize(text: str) -> list[str]:
    """Lowercase, split on non-alphanumeric, remove stop words and short tokens."""
    words = re.findall(r"[a-z0-9_]+", text.lower())
    return [w for w in words if w not in _STOP_WORDS and len(w) > 1]


class SkillRouter:
    """Routes eval prompts to relevant skills using BM25 + utterance matching.

    Two-stage scoring:
    1. BM25 against skill SKILL.md descriptions (content-based)
    2. Utterance overlap bonus (bridges natural language → technical terms)

    Usage:
        router = SkillRouter(skills_dir)
        top_skills = router.route(eval_prompt, top_n=2)
    """

    def __init__(self, skills_dir: str, top_n: int = 2, threshold: float = 0.05):
        self.top_n = top_n
        self.threshold = threshold
        self.skills: dict[str, dict] = {}

        skills_path = Path(skills_dir)
        for md in sorted(skills_path.rglob("SKILL.md")):
            name = md.parent.name
            content = md.read_text(encoding="utf-8")

            if content.startswith("---"):
                end = content.find("---", 3)
                if end != -1:
                    content = content[end + 3:].strip()

            lines = content.split("\n")
            desc_lines = []
            for line in lines[1:20]:
                if line.strip() == "" and desc_lines:
                    break
                if line.strip() and not line.startswith("#"):
                    desc_lines.append(line)
            description = " ".join(desc_lines) if desc_lines else content[:500]

            self.skills[name] = {
                "description": description,
                "tokens": tokenize(description),
                "content": content,
            }

        # Compute IDF across all skills
        doc_freq: Counter = Counter()
        for skill in self.skills.values():
            for token in set(skill["tokens"]):
                doc_freq[token] += 1

        n_docs = len(self.skills)
        self.idf: dict[str, float] = {}
        for token, freq in doc_freq.items():
            self.idf[token] = math.log((n_docs + 1) / (freq + 1)) + 1

        # Pre-tokenize utterances
        self.utterances: dict[str, list[list[str]]] = {}
        for skill_name, phrases in SKILL_UTTERANCES.items():
            self.utterances[skill_name] = [tokenize(p) for p in phrases]

    def _bm25_score(self, prompt_tokens: list[str], skill_tokens: list[str]) -> float:
        """BM25 scoring between prompt and skill description."""
        if not prompt_tokens or not skill_tokens:
            return 0.0

        k1 = 1.5
        b = 0.75
        avg_dl = 50
        dl = len(skill_tokens)
        skill_tf = Counter(skill_tokens)

        score = 0.0
        for token in set(prompt_tokens):
            tf = skill_tf.get(token, 0)
            if tf == 0:
                continue
            idf = self.idf.get(token, 1.0)
            numerator = tf * (k1 + 1)
            denominator = tf + k1 * (1 - b + b * dl / avg_dl)
            score += idf * (numerator / denominator)

        max_possible = len(set(prompt_tokens)) * (k1 + 1)
        return score / max_possible if max_possible > 0 else 0.0

    def _utterance_score(self, prompt_tokens: list[str], skill_name: str) -> float:
        """Score based on utterance overlap — bridges natural language to skills."""
        if skill_name not in self.utterances:
            return 0.0

        prompt_set = set(prompt_tokens)
        best_score = 0.0

        for ut_tokens in self.utterances[skill_name]:
            if not ut_tokens:
                continue
            overlap = prompt_set & set(ut_tokens)
            if overlap:
                # Jaccard-like but biased toward utterance coverage
                score = len(overlap) / len(ut_tokens)
                best_score = max(best_score, score)

        return best_score

    def route(self, eval_prompt: str, top_n: Optional[int] = None, threshold: Optional[float] = None) -> list[str]:
        """Return top-N skill names relevant to the eval prompt."""
        n = top_n or self.top_n
        thresh = threshold if threshold is not None else self.threshold

        prompt_tokens = tokenize(eval_prompt)

        scores = []
        for name, skill in self.skills.items():
            bm25 = self._bm25_score(prompt_tokens, skill["tokens"])
            utt = self._utterance_score(prompt_tokens, name)
            # Combine: utterance match is a strong signal (weighted 2x)
            combined = bm25 + utt * 2.0
            if combined >= thresh:
                scores.append((name, combined, bm25, utt))

        scores.sort(key=lambda x: -x[1])
        return [name for name, _, _, _ in scores[:n]]

    def route_with_scores(self, eval_prompt: str) -> list[tuple[str, float]]:
        """Return all skills with combined scores (for debugging)."""
        prompt_tokens = tokenize(eval_prompt)
        scores = []
        for name, skill in self.skills.items():
            bm25 = self._bm25_score(prompt_tokens, skill["tokens"])
            utt = self._utterance_score(prompt_tokens, name)
            combined = bm25 + utt * 2.0
            scores.append((name, combined))
        scores.sort(key=lambda x: -x[1])
        return scores

    def get_skill_content(self, name: str) -> Optional[str]:
        """Get full skill content by name."""
        skill = self.skills.get(name)
        return skill["content"] if skill else None
