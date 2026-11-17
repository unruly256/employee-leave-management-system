(() => {
  'use strict';

  const modalElement = document.getElementById('actionConfirmModal');
  const confirmButton = document.getElementById('confirmActionButton');
  const titleElement = document.getElementById('actionConfirmTitle');
  const messageElement = document.getElementById('actionConfirmMessage');
  let pendingForm = null;

  // ---- Confirmation dialog ------------------------------------------------
  // Add data-confirm="Message" to a form. Optional: data-confirm-title, data-confirm-label,
  // data-confirm-variant ("danger" by default, or "primary").
  function openConfirm(form) {
    pendingForm = form;
    const variant = form.dataset.confirmVariant || 'danger';
    messageElement.textContent = form.dataset.confirm;
    titleElement.textContent = form.dataset.confirmTitle || 'Please confirm';
    confirmButton.className = `btn btn-${variant}`;
    confirmButton.querySelector('.label').textContent = form.dataset.confirmLabel || 'Continue';
    bootstrap.Modal.getOrCreateInstance(modalElement).show();
  }

  confirmButton?.addEventListener('click', () => {
    if (!pendingForm) return;
    const form = pendingForm;
    pendingForm = null;
    form.dataset.confirmed = 'true';
    bootstrap.Modal.getOrCreateInstance(modalElement).hide();
    form.requestSubmit();
  });

  modalElement?.addEventListener('hidden.bs.modal', () => { pendingForm = null; });

  // ---- Form submission: confirm first, then lock the button once --------------
  document.addEventListener('submit', (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement)) return;

    if (form.dataset.confirm && form.dataset.confirmed !== 'true') {
      event.preventDefault();
      if (modalElement && window.bootstrap) openConfirm(form);
      else if (window.confirm(form.dataset.confirm)) { form.dataset.confirmed = 'true'; form.requestSubmit(); }
      return;
    }

    if (form.hasAttribute('data-disable-submit')) {
      const submit = form.querySelector('[type="submit"]');
      if (!submit) return;
      // Wait a tick so the browser still submits normally, then block repeat clicks.
      window.setTimeout(() => {
        submit.dataset.originalHtml = submit.innerHTML;
        submit.disabled = true;
        submit.innerHTML = '<span class="spinner-border spinner-border-sm" aria-hidden="true"></span>Working…';
      }, 0);
    }
  });

  // Coming back with the browser's Back button must not leave a button stuck on "Working…".
  window.addEventListener('pageshow', (event) => {
    if (!event.persisted) return;
    document.querySelectorAll('[data-original-html]').forEach((button) => {
      button.disabled = false;
      button.innerHTML = button.dataset.originalHtml;
    });
    document.querySelectorAll('form[data-confirmed]').forEach((form) => delete form.dataset.confirmed);
  });

  // ---- Flash messages: success and info fade away, problems stay until closed ---
  document.querySelectorAll('.flash-stack .alert-success, .flash-stack .alert-info').forEach((alert) => {
    window.setTimeout(() => {
      if (window.bootstrap && document.body.contains(alert)) bootstrap.Alert.getOrCreateInstance(alert).close();
    }, 5500);
  });
})();
