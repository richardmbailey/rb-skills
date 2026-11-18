# GPT-6.2 conversations in the Responses API

Apply this reference when an application manages conversations for multiple agents using the Responses API. The runner decides which role, user and organisation may receive each item.

## Continue one worker

Put reusable instructions in a `developer` message at the beginning of `input`. GPT-6.2 appends top-level `instructions` after the input. Use that field for guidance specific to the current request. In this example, the worker checks supplied figures and the current reply must include the calculation.

```json
{
  "model": "gpt-6.2-sol",
  "reasoning": {"effort": "medium"},
  "input": [
    {"role": "developer", "content": "Check the supplied figures and identify the evidence for each correction."},
    {"role": "user", "content": "The July count is 12 and the August count is 18. Check the stated total of 29."}
  ],
  "instructions": "Give the corrected total and its calculation in this reply."
}
```

When the same worker continues, leave earlier messages, tool calls and results in their original order. Append new corrections, clarifications and tool outputs. Editing the conversation prefix can discard prior reasoning items and cause repeated work. A stable prefix keeps earlier input eligible for prompt caching. A cache hit is a separate observation. [OpenAI guidance on preserving the prefix](https://developers.openai.com/api/docs/guides/keep-prefix-unchanged)

Certain model changes, including downgrades, and changes of end user or organisation also discard prior reasoning items. Keep the next step recoverable from explicit decisions, accepted evidence and pending work. When an eligible Zero Data Retention integration manages history itself, pass the prior output items back in order, including the encrypted reasoning items required for continuity. Follow the application's retention and access policy. [OpenAI GPT-6.2 migration guide](https://developers.openai.com/api/docs/guides/latest-model/gpt-6.2-astra#migration-quickstart)

## Start an independent role

Give an independent reviewer a fresh conversation with its own developer instructions and the authorised evidence it needs. For example, a reviewer may need the requirements, proposed change and test receipt. Exclude the implementer's private reasoning. Across user or organisation boundaries, start from the new identity's authorised inputs.

## Check the integration

- Inspect the requests produced by the actual adapter. Test two turns of one worker, including a correction or tool result. Check the first developer message, order of prior items and scope of per-request instructions.
- Test a new reviewer and a change of identity. Verify that each receives only its permitted evidence. Exercise recovery from a model change using the recorded work state.
- GPT-6.2 tool calling requires Responses. On this endpoint omit `temperature`, `top_p` and `top_logprobs`, and remove `message.output_text.logprobs` from `include`. Check the request after framework defaults have been applied. [OpenAI model parameter guidance](https://developers.openai.com/api/docs/guides/latest-model/gpt-6.2-astra#migration-quickstart)

The RB constrained runtime has separately qualified provider profiles. Changing one requires its own qualification of the model, adapter settings, authority bindings and acceptance results. This reference applies to application design.
