// Default feature stub from templates/extension/side-panel. A recipe replaces this file
// (recipes/<slug>/src/feature/index.ts) with the extension's real feature.
export function mount(root: HTMLElement): void {
  const note = document.createElement("p");
  note.textContent = "Feature not implemented yet.";
  note.dataset.testid = "feature-stub";
  root.append(note);
}
