# Latest — editable text restoration

- Restore text recording, model-assisted removal of lettering, and native editable text reinsertion; no specific image model is required.
- Save original canvas dimensions, label coordinates, bounds and baseline metadata in a per-job manifest; map source pixels to the vector canvas.
- Correct PowerPoint text anchoring and rotation, and shared-pivot multiline SVG rotation. Add text-restoration and coordinate regression tests.
- Retain remaining-credit reporting and both drawing backends in the standalone cell_su7 repository.

# 0.3.0 — cell_su7

- Unify both distributions under cell_su7 with user-selected PPT / Illustrator drawing.
- Send original images directly to path recognition; remove text cleanup and reinsertion.
- Preserve backend-specific rendering, cache schemas, ordering and post-processing.

# Changelog

## 0.2.0 - Unreleased

- Use one reconstruction, text, SVG parsing, culling, cache, batching, and native-object contract on Windows and macOS.
- Keep live PowerPoint COM drawing on Windows and add native editable OOXML output for saved PPTX files on macOS.
- Add macOS Keychain credential storage, cross-platform installation, and diagnostics.
- Move stable runtime values into `platform-contract.json`; remove frozen manifests and fixed-tag installation requirements.
- Allow a user-supplied chat API key to be configured automatically through stdin without echoing it.
- Add install-time OS, Python, PowerPoint/WPS, credential, and backend matching with a non-secret runtime profile.
- Add automatic dependency installation and native editable OOXML fallback when live presentation automation is unavailable.

## 0.1.1 - 2026-08-27

- Describe the product consistently as live PowerPoint drawing rather than path presentation.
- Rename drawing-cache state and runtime contract fields while preserving bottom-to-top editable drawing behavior.
- Align the GitHub homepage with the established stable-plugin documentation structure.

## 0.1.0 - 2026-08-27

- Freeze the tested cell_su7 PowerPoint drawing workflow.
- Add live editable text, native freeform paths, single-cache drawing, hidden-path culling, and existing-slide protection.
- Add locked dependencies, DPAPI credential storage, package tests, PowerPoint end-to-end tests, release ZIP, and SHA256 verification.
