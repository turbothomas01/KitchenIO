function setupDialogs() {
  document.querySelectorAll('[aria-haspopup="dialog"][aria-controls]').forEach((button) => {
    const dialog = document.getElementById(button.getAttribute('aria-controls'));
    if (!dialog) return;

    button.addEventListener('click', () => {
      if (typeof dialog.showModal === 'function') {
        dialog.showModal();
      } else {
        dialog.setAttribute('open', '');
      }
      const firstInput = dialog.querySelector('input:not([type="hidden"]), textarea, select, button');
      if (firstInput) firstInput.focus();
    });
  });
}

document.addEventListener('DOMContentLoaded', setupDialogs);
