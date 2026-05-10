function activateTab(tab) {
  const tablist = tab.closest('[role="tablist"]');
  const tabs = Array.from(tablist.querySelectorAll('[role="tab"]'));

  tabs.forEach((candidate) => {
    const selected = candidate === tab;
    const panel = document.getElementById(candidate.getAttribute('aria-controls'));
    candidate.setAttribute('aria-selected', String(selected));
    candidate.tabIndex = selected ? 0 : -1;
    if (panel) {
      panel.hidden = !selected;
    }
  });

  tab.focus();
}

function tabForCurrentHash(tabs) {
  if (!window.location.hash) {
    return tabs[0];
  }
  const panelId = window.location.hash.slice(1);
  return tabs.find((tab) => tab.getAttribute('aria-controls') === panelId) || tabs[0];
}

document.addEventListener('DOMContentLoaded', () => {
  const tabs = Array.from(document.querySelectorAll('[role="tab"]'));
  if (tabs.length === 0) {
    return;
  }

  tabs.forEach((tab, index) => {
    tab.addEventListener('click', () => {
      activateTab(tab);
      const panelId = tab.getAttribute('aria-controls');
      if (panelId) {
        history.replaceState(null, '', `#${panelId}`);
      }
    });

    tab.addEventListener('keydown', (event) => {
      const isForward = event.key === 'ArrowRight' || event.key === 'ArrowDown';
      const isBackward = event.key === 'ArrowLeft' || event.key === 'ArrowUp';
      const isHome = event.key === 'Home';
      const isEnd = event.key === 'End';

      if (!isForward && !isBackward && !isHome && !isEnd) {
        return;
      }

      event.preventDefault();
      let nextIndex = index;
      if (isForward) nextIndex = (index + 1) % tabs.length;
      if (isBackward) nextIndex = (index - 1 + tabs.length) % tabs.length;
      if (isHome) nextIndex = 0;
      if (isEnd) nextIndex = tabs.length - 1;
      activateTab(tabs[nextIndex]);
    });
  });

  activateTab(tabForCurrentHash(tabs));
});
