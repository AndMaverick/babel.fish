"""babel.fish: cultural calibration for translation. Tone and context profiles, protected spans, and a verifier that catches changed numbers,
lost placeholders, untranslated or wrong-language output, the wrong form of address and missing terminology. Standard library only."""
from ._version import __version__
from .backends import AnthropicMessages, Backend, FixtureBackend, OpenAICompatible
from .errors import BabelError, BackendError
from .glossary import Glossary
from .pipeline import Cache, Result, translate
from .profiles import Profile
from .verify import check

_STYLE = {"default": ("general", "formal"), "law": ("legal", "formal"), "marketing": ("marketing", "casual"), "pitch": ("pitch", "casual")}


def babel_fish(text: str, lang: str, style: str = "default") -> str:
    """The original one-call API: translate ``text`` into ``lang`` with one of the original styles (default, law, marketing, pitch)."""
    from .backends import from_environment

    context, tone = _STYLE.get(style, _STYLE["default"])
    return translate(text, Profile(lang, tone, context), from_environment(None, None, None)).text


__all__ = ["AnthropicMessages", "BabelError", "Backend", "BackendError", "Cache", "FixtureBackend", "Glossary", "OpenAICompatible", "Profile",
           "Result", "__version__", "babel_fish", "check", "translate"]
