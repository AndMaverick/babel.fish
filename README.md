<div align="center">

# 🌍🐠 Babel.Fish
*From translation → to true cultural fluency.*

![Status](https://img.shields.io/badge/status-Active-brightgreen)
![Version](https://img.shields.io/badge/version-0.2.0-yellow)
![License](https://img.shields.io/badge/license-MIT-lightgrey)
![Dependencies](https://img.shields.io/badge/dependencies-none-blue)

</div>

Most systems can translate. Few can adapt, and almost none can prove the result is still true.

Babel.Fish does two jobs. It builds a precise instruction for any language model: who the reader is, which form of address to use, what the context demands, which terms are fixed. Then it checks what comes back with a deterministic verifier and, when the check fails, sends the model the exact problems and asks again. A translation that changes "20 %" into "25 %", drops a placeholder, answers in the wrong language, or switches from "Sie" to "du" does not get through quietly.

Standard library only. Python 3.10 to 3.13. Works with any OpenAI compatible server (including local ones) and with the Anthropic Messages API.

## Install and run

```bash
pip install .
export OPENAI_API_KEY=...            # or ANTHROPIC_API_KEY with --model
babel-fish translate --text "Our product reduces costs by 20%." --to de --tone formal
```

The original command line still works:

```bash
python babel_fish.py --input "Our product reduces costs by 20%." --lang de --tone formal
python babel_fish.py --input "Our product reduces costs by 20%." --lang fr --tone casual
python babel_fish.py --input "Our product reduces costs by 20%." --lang en --context investor
```

Languages: `en`, `de`, `fr`, `es`. Tones: `formal`, `casual`. Contexts: `general`, `legal`, `investor`, `marketing`, `technical`, `pitch`.

## The verifier works without a model

Checking an existing translation needs no network and no key:

```text
$ babel-fish verify --source examples/source.txt --output examples/de_good.txt --to de --tone formal
no problems found

$ babel-fish verify --source examples/source.txt --output examples/de_wrong_number.txt --to de --tone formal
error: number_missing: numbers in the source that the output lacks or changed: 20
warning: number_added: numbers in the output that the source does not have: 25

$ babel-fish verify --source examples/source.txt --output examples/de_wrong_register.txt --to de --tone formal
error: register: informal German address (du-forms) in a formal text: deine
```

Exit code 0 means no errors, 1 means the text has errors, 2 means the input could not be used. That makes it a gate in a localisation pipeline: whatever produced the translation, a person, a vendor or a model, the same checks run.

| Check | What it catches |
| --- | --- |
| Numbers | A figure that changed or went missing. Numbers are compared by value across conventions, so "1,200,000" in English and "1.200.000" in Spanish match, and number words from two to one hundred are understood ("twenty" equals "20", "zwanzig" equals "20"). |
| Dates and times | Compared as sets of integers, so "2026-03-15" and "15.03.2026" and "15/03/2026" agree and "16.03.2026" does not. |
| Protected spans | Placeholders such as `{name}`, `%s`, URLs and email addresses are masked before the model sees them and put back afterwards. If one is lost, that is an error. |
| Untranslated output | The model returned the source unchanged. |
| Wrong language | The reply is identifiably in another language. |
| Refusals and preambles | "I'm sorry, I cannot translate this", "Here is the translation:" and similar. |
| Register | Sie or du, vous or tu, usted or tú, and contractions or slang in formal English. |
| Terminology | Required translations and names that must stay untouched (a JSON glossary). |
| Length | Replies far shorter or longer than the source suggests. |

## Calibration

`babel-fish prompt` prints what the model is told, offline:

```text
$ babel-fish prompt --to de --tone formal --context investor
You are a professional translator and localisation editor. Translate the user's text into German. Reply with the translation only: no preamble, no notes, no quotation marks around it.
Address the reader as "Sie" (capitalised) and never use "du" forms.
Write for an investor audience: confident, precise and free of hype; keep every figure exact.
Write numbers the way German does (for example 1.234,56), without changing any value.
Do not add, drop or change any number, date, name or claim.
```

## The repair loop

`translate` sends the request, runs the verifier, and if there are errors sends a second request that quotes the failed output and lists each problem. After the last attempt it returns the best reply (fewest errors, later wins a tie) and says plainly whether it passed. Every attempt is recorded with the SHA-256 of the exact request, so a result can be traced and a repeat run costs nothing: `--cache file.jsonl` answers identical requests from disk.

```python
from babel_fish import Profile, translate
from babel_fish.backends import OpenAICompatible

result = translate("Our product reduces costs by 20%.", Profile("de", "formal", "investor"), OpenAICompatible("gpt-4o-mini"))
print(result.ok, result.text, len(result.attempts))
```

Backends are small and replaceable: `OpenAICompatible(model, base_url)`, `AnthropicMessages(model)`, and `FixtureBackend` for tests. They retry on 429 and 5xx, honour `Retry-After` (capped at 20 seconds), never retry client errors, and never put the key in an error message.

## What was measured

`python examples/evaluate.py` runs the verifier on a handwritten parallel corpus (20 English sentences with formal German, French and Spanish translations, informal variants and wrong terminology variants). Nothing in it calls a model.

```text
clean translations flagged with an error: 0 of 60
language identified correctly on the correct translations: 54 of 60
broken translations caught:
  empty               60 of 60
  left untranslated   60 of 60
  number changed      39 of 39
  number dropped      39 of 39
  placeholder lost     9 of 9
  preamble added      60 of 60
  translation refused  60 of 60
  wrong language      54 of 60
  wrong register      18 of 18
  wrong term           3 of 3
one wrong number, repaired on the second attempt: 39 of 39
```

CI runs this on every push, along with 52 unit tests (a local HTTP server stands in for the providers), ruff, and strict mypy.

## Honest limits

- **The corpus is small and written by one person.** Zero false alarms on 60 correct translations is a real result and a modest one. Treat it as evidence the checks are not trigger happy, not as a guarantee on your text.
- **Language identification needs words.** Six of the 60 correct translations were returned as "unknown" (short sentences or sentences made mostly of numbers), so a wrong language reply to such a sentence is not caught: 54 of 60. It never called a correct translation the wrong language in the corpus. It abstains instead of guessing.
- **Register checks are word lists.** They catch "du" where "Sie" was required. They say nothing about whether the prose is elegant or idiomatic.
- **Number words are understood from two to one hundred.** Larger spelled out numbers are not compared. Digits are compared at any size.
- **Dates are compared as sets of integers.** A swapped day and month ("03.04" for "04.03") is not caught.
- **This does not measure translation quality.** It checks that what must not change did not change and that what was asked for is present. Whether a particular model writes a pitch that persuades a Parisian creative director is a question for people who read French. No live model result is claimed here, because none was run.

## Layout

```text
babel_fish/        numbers, numwords, langid, protect, register, glossary, verify, profiles, prompt, backends, pipeline, cli
babel_fish.py      launcher for the original command
tests/             52 tests and the hand-written corpus
examples/          evaluate.py and sample inputs
```

## Roadmap

- [x] Spanish alongside English, German and French
- [x] Context profiles for legal, investor, marketing, technical and pitch text
- [x] Verifier, repair loop, cache, two backends
- [ ] More languages (each needs a number convention, stop words and a register rule)
- [ ] Style mirroring from a sample of the target voice
- [ ] A published benchmark of live models against the verifier

## License

Released under the [MIT License](LICENSE).

<p align="center">
💎 ✨ 🏛️ ✨ 💎 <br>
<b>AndMaverick, Ars ex Machina</b> <br>
💎 ✨ 🏛️ ✨ 💎
</p>
