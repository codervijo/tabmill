// Default feature stub from templates/extension/maps-overlay. A recipe replaces this file.
export interface OverlayContext {
  /** The overlay's host element (remove it to close the overlay). */
  host: HTMLElement;
  /** Shadow root for extra layers/styles the feature adds. */
  shadow: ShadowRoot;
}

export function mount(root: HTMLElement, _ctx?: OverlayContext): void {
  const note = document.createElement("p");
  note.textContent = "Feature not implemented yet.";
  note.dataset.testid = "feature-stub";
  root.append(note);
}
