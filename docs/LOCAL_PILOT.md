# Local-model pilot

The optional `pilot` command uses the same public task, tool, and memory
interfaces with model-selected actions from a local Ollama server. It writes to a
separate output directory. CI uses the deterministic offline fixtures.

Start a local Ollama server and pull two tool-calling models from distinct
families. For example, use the following Ollama model tags.

```powershell
ollama pull qwen3:4b
ollama pull llama3.2:3b
.venv/Scripts/trajyn.exe pilot --source-model qwen3:4b --target-model llama3.2:3b
```

Use `--ollama-url` for a different loopback port. The adapter looks up the
locally installed model digests and architecture families. It records the
server version and inference settings. By default the pilot uses source seeds
0–3, test seeds 200 and 202, all five paired conditions, and eight actions per
attempt. It requests a 4096-token context, up to 160 output tokens per call,
temperature zero, inference seed 17, and a 30-second HTTP timeout. That plan
allows up to 112 calls. Experimental results may vary across hardware, software,
and model digests.

The default `--tool-mode native` requests Ollama function calls.
`--tool-mode json` constrains the model's response to a valid tool and argument
shape. The model still selects the action and fills its arguments. Use
`--inference-timeout` to record a longer limit for slow model startup.
The report also records the prompt revision. The prompt encourages the model
to advance from the public history and retry only after a recoverable failure.

The pilot keeps all collected source traces, including failures. It induces
capsules only from independently verified and groundable traces. If no source
qualifies, the pilot records that outcome before ending. When a target run
is possible it exports the same paired reports and records model calls,
reported tokens, and termination status in `pilot.json`. Memory delivery is
observable. Whether a model used it internally is unknown.

This is a hardware and workflow pilot. The small fixed sample and condition
order support descriptive reporting. Model startup and caching can affect
timings, and successful task execution alone cannot establish a transfer benefit.

## Feasibility attempts

The initial runs used Ollama 0.40.16 and kept source seeds 0–3 and target seeds
200 and 202 fixed.

| Source | Action mode | Verified sources | Observation |
| --- | --- | ---: | --- |
| `qwen3:4b` | Native | 0/4 | One request timed out and three responses contained no function call. |
| `qwen3:4b` | JSON, initial prompt | 0/4 | All four attempts exhausted the action budget repeating `read_case`. |

Both runs stopped before target evaluation because induction requires a
verified source. Their metadata is archived with the
[native attempt](../examples/local-pilot/qwen3-4b-native.json) and
[initial JSON attempt](../examples/local-pilot/qwen3-4b-json.json).
