# Self-Reflection

Begin with a concise checklist (3-7 bullets) outlining the main sub-tasks you will perform in this review.

Review the chat history to analyze interactions between the assistant and the user.

## Misunderstandings
- Highlight any miscommunications or misunderstandings.
- Identify the root causes, focusing on missing context or unclear information that led to the issues.
- Formulate a process to ensure that sufficient context is always established to prevent similar issues in the future.
- Produce a set of actionable rules for inclusion in the `copilot-instructions.md` file, aimed at improving assistant workflows and enhancing user outcomes.

## Engineering
- Document errors or failures encountered during development, especially recurring ones.
- Reflect on the missing context that could have prevented these errors.
- Assess if any test coverage could have detected or avoided runtime failures.
- Propose workflow practices to strengthen context retrieval, documentation, and test coverage, with the objective to minimize future errors.

After substantive changes or tool calls, validate the outcome in 1-2 lines and proceed or self-correct if needed.

# Outcome
- Out of all the new rules, select the single most impacting rule and integrate that into the existing instructions. Ensure that all instructions are harmonized; if prioritization is needed, clearly order rules from most to least important.
- Update the `copilot-instructions.md` file to reflect the latest, unified rules.

Set reasoning_effort = medium, ensuring a balance between detail and conciseness appropriate to this self-reflection and integration task.