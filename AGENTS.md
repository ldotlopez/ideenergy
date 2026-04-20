# AGENTS.md - Coding Guidelines

Follow these standards for all contributions:

## Python Best Practices
- **PEP 8:** Follow standard Python style guidelines.
- **Type Hinting:** Use strict type hints for all functions, methods, and variables.
- **Async/Await:** All IO-bound operations must be non-blocking and asynchronous.

## Home Assistant & HACS Standards
- **Architecture:** Keep logic decoupled. Use `asyncio` for integrations.
- **Config Flow:** Use `data_entry_flow` for integrations. Ensure translations are provided in `translations/en.json`.
- **Entity Management:** Use `Entity` base class. Implement `update` logic using coordinator pattern where applicable.
- **HACS:** Include a valid `manifest.json` with all required fields (domain, name, config_flow, etc.).
- **Error Handling:** Gracefully handle API failures with appropriate logging and user notifications (via `config_flow` or `Entity` error states).

## Testing
- **Unit Tests:** All new functionality must have corresponding tests in the `tests/` directory.
- **Mocking:** Mock all external API calls using `unittest.mock` (or similar).
- **Standards:** Tests must be deterministic and run efficiently.
