/* Live preview on the "Apply for leave" page: counts days with the same rules as the server
   (Mon–Fri minus public holidays, or every day when the system is set to calendar days). The
   server still makes the final decision when the form is submitted. */
(() => {
  'use strict';
  const form = document.getElementById('leaveForm');
  if (!form) return;

  const holidays = new Set(); // no JSON data: public holidays are checked by the server on submit
  const types = {}; // no JSON data: balance preview removed; the server checks balances on submit
  const calendarBasis = form.dataset.basis === 'calendar';

  const typeField = form.querySelector('#id_leave_type');
  const startField = form.querySelector('#id_start_date');
  const endField = form.querySelector('#id_end_date');
  const box = document.getElementById('estimate');
  const headline = box.querySelector('strong');
  const detail = box.querySelector('span');
  const icon = box.querySelector('.bi');

  const parse = (value) => {
    const [y, m, d] = value.split('-').map(Number);
    return new Date(y, m - 1, d);
  };
  const iso = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  const pretty = (d) => d.toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' });
  const plural = (n, word) => `${n} ${word}${n === 1 ? '' : 's'}`;

  function countDays(start, end) {
    let total = 0;
    for (let d = new Date(start); d <= end; d.setDate(d.getDate() + 1)) {
      if (calendarBasis || (d.getDay() !== 0 && d.getDay() !== 6 && !holidays.has(iso(d)))) total += 1;
    }
    return total;
  }

  function show(state, iconName, title, text) {
    box.className = `estimate is-${state}`;
    icon.className = `bi bi-${iconName}`;
    headline.textContent = title;
    detail.textContent = text;
  }

  function update() {
    const info = types[typeField.value];
    if (!startField.value || !endField.value) {
      show('idle', 'calendar-event', 'Choose your dates',
        info ? 'The number of leave days will appear here.' : 'Pick a leave type and dates to see how many days this will use.');
      return;
    }
    const start = parse(startField.value);
    const end = parse(endField.value);
    if (end < start) {
      show('over', 'exclamation-triangle-fill', 'The end date is before the start date', 'Move the end date to the same day or later.');
      return;
    }
    const days = countDays(start, end);
    const range = start.getTime() === end.getTime() ? pretty(start) : `${pretty(start)} to ${pretty(end)}`;
    if (days === 0) {
      show('over', 'exclamation-triangle-fill', 'No leave days in this range',
        `${range} only covers weekends or public holidays, so there is nothing to apply for.`);
      return;
    }
    const unit = calendarBasis ? 'day' : 'working day';
    if (info && info.left !== null && info.allowed) {
      if (days > info.left) {
        show('over', 'exclamation-triangle-fill', `${plural(days, unit)} is more than you have left`,
          `${info.name} leave: ${plural(Math.max(info.left, 0), 'day')} remaining this year. ${range}.`);
      } else {
        show('ok', 'check-circle-fill', plural(days, unit),
          `${range}. You will have ${plural(info.left - days, 'day')} of ${info.name} leave left.`);
      }
    } else {
      show('ok', 'check-circle-fill', plural(days, unit), `${range}.`);
    }
  }

  startField.addEventListener('change', () => {
    endField.min = startField.value;
    if (startField.value && (!endField.value || endField.value < startField.value)) endField.value = startField.value;
    update();
  });
  [typeField, endField, form.querySelector('#id_employee')].forEach((el) => el && el.addEventListener('change', update));
  if (startField.value) endField.min = startField.value;
  update();
})();
