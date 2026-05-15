# Coding Standards

Reference when writing or reviewing non-trivial code. These supplement the default system prompt; user and project instructions take precedence.

## Naming
- `snake_case` for database schemas, tables, and columns
- BEM (`block__element--modifier`) for CSS class names
- Descriptive, intent-revealing identifiers — avoid single-letter names except loop indices

## SOLID
- **SRP** — one reason to change per class or module
- **OCP** — extend behavior via new code; don't modify verified code
- **LSP** — subtypes must be fully substitutable for their base types
- **ISP** — many small, specific interfaces over one general-purpose interface
- **DIP** — depend on abstractions, not concrete implementations

## Architecture
- Favor composition over inheritance; avoid deep hierarchies
- Layer by responsibility: Presentation → Business/Domain → Data Access
- Domain layer defines interfaces; infrastructure implements them (Dependency Inversion)
- Enforce Separation of Concerns — each layer owns one kind of decision

## Design Patterns
Apply when the problem fits the pattern. Never force-fit.

- **Creational:** Factory Method, Abstract Factory, Builder, Singleton
- **Structural:** Adapter, Decorator, Facade, Proxy
- **Behavioral:** Strategy, Observer, Command, State

## Testing
- Testing pyramid: broad base of unit tests, fewer integration tests, fewest end-to-end tests
- Unit tests are isolated — no shared mutable state between tests
- Integration tests hit real dependencies where trust in the boundary matters
- One behavior per test; prefer failure messages that name the expected behavior

## Security
- Validate and sanitize at every system boundary (user input, external APIs, file I/O)
- Reject implicit trust between services — authenticate and authorize at each hop
- Log detailed errors (stack, context) internally; return generic, safe errors to clients
- Never leak stack traces, internal paths, config, or framework details in responses

## Error Handling
- Centralize error handling at layer boundaries, not scattered per call site
- Catch exceptions only where you can meaningfully recover or translate them
- Fail loudly in development; degrade gracefully in production

## Delivery
- Trunk-based development with short-lived branches and atomic commits
- Automate lint, build, test, and deploy in CI/CD
- Instrument with distributed tracing and centralized logging (APM) for production observability
