# Tool security and least privilege

Least-privilege tool execution means giving each tool only the permissions needed for its task. Retrieval tools should read only from the indexed corpus. They should not accept arbitrary filesystem paths, run shell commands, expose secrets, or access unrelated user data.

Validate inputs, cap result counts, normalize source identifiers, and return explicit errors for unknown IDs. Avoid passing untrusted model-generated strings directly to SQL, a shell, or a path-opening function. Use parameterized database queries and allow-listed operations where applicable.

Read-only tools reduce the impact of a mistaken or malicious tool call. If write actions are introduced, require explicit authorization, enforce a narrowly scoped target, log the action, and provide a way to review or reverse it where possible.