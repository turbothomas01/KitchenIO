function setupTabs() {
  const tabs = Array.from(document.querySelectorAll('[role="tab"]'));
  const addButton = document.getElementById('open-active-dialog');
  if (!tabs.length || !addButton) return;

  function activate(tab, options = {}) {
    tabs.forEach((candidate) => {
      const selected = candidate === tab;
      candidate.setAttribute('aria-selected', String(selected));
      candidate.tabIndex = selected ? 0 : -1;
      const panel = document.getElementById(candidate.getAttribute('aria-controls'));
      if (panel) panel.hidden = !selected;
    });

    const isShopping = tab.id === 'shopping-tab';
    const label = isShopping ? addButton.dataset.shoppingLabel : addButton.dataset.productsLabel;
    const dialog = isShopping ? addButton.dataset.shoppingDialog : addButton.dataset.productsDialog;
    addButton.setAttribute('aria-label', label);
    addButton.setAttribute('title', label);
    addButton.setAttribute('aria-controls', dialog);

    if (options.updateHash) {
      const panelId = tab.getAttribute('aria-controls');
      if (panelId) history.replaceState(null, '', `#${panelId}`);
    }
  }

  tabs.forEach((tab) => {
    tab.addEventListener('click', () => activate(tab, { updateHash: true }));
    tab.addEventListener('keydown', (event) => {
      const current = tabs.indexOf(tab);
      let next = null;
      if (event.key === 'ArrowRight') next = tabs[(current + 1) % tabs.length];
      if (event.key === 'ArrowLeft') next = tabs[(current - 1 + tabs.length) % tabs.length];
      if (event.key === 'Home') next = tabs[0];
      if (event.key === 'End') next = tabs[tabs.length - 1];
      if (!next) return;
      event.preventDefault();
      activate(next, { updateHash: true });
      next.focus();
    });
  });

  const initialPanelId = window.location.hash.replace('#', '');
  const initialTab = tabs.find((tab) => tab.getAttribute('aria-controls') === initialPanelId);
  if (initialTab) activate(initialTab);
}

document.addEventListener('DOMContentLoaded', setupTabs);
