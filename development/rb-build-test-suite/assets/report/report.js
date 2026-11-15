'use strict';
// Progressive enhancement only: all evidence is present without this script.
const controls = document.getElementById('controls');
controls.hidden = false;
const checks = Array.from(document.querySelectorAll('.check'));
function filterChecks() {
  const query = document.getElementById('search').value.toLocaleLowerCase();
  const state = document.getElementById('state').value;
  const required = document.getElementById('required').value;
  const capability = document.getElementById('capability').value;
  checks.forEach(check => {
    check.hidden = !check.textContent.toLocaleLowerCase().includes(query) ||
      Boolean(state && check.dataset.state !== state) ||
      Boolean(required && check.dataset.required !== required) ||
      Boolean(capability && check.dataset.capability !== capability);
  });
  document.getElementById('filter-count').textContent =
    checks.filter(check => !check.hidden).length + ' of ' + checks.length +
    ' attempts visible. Filters change this view only; the saved gate is unchanged.';
}
controls.addEventListener('input', filterChecks);
filterChecks();
document.querySelectorAll('table').forEach(table => {
  Array.from(table.tHead.rows[0].cells).forEach((heading, column) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = heading.textContent + ' ↕';
    button.setAttribute('aria-label', 'Sort by ' + heading.textContent);
    heading.textContent = '';
    heading.appendChild(button);
    button.addEventListener('click', () => {
      const ascending = heading.getAttribute('aria-sort') !== 'ascending';
      Array.from(table.tHead.rows[0].cells).forEach(cell => cell.removeAttribute('aria-sort'));
      heading.setAttribute('aria-sort', ascending ? 'ascending' : 'descending');
      const rows = Array.from(table.tBodies[0].rows);
      rows.sort((a, b) => (ascending ? 1 : -1) *
        a.cells[column].textContent.localeCompare(b.cells[column].textContent, undefined, {numeric:true}));
      rows.forEach(row => table.tBodies[0].appendChild(row));
    });
  });
});
// Print the complete content even after filtering or closing details.
let closedDetails = [];
window.addEventListener('beforeprint', () => {
  closedDetails = Array.from(document.querySelectorAll('details:not([open])'));
  closedDetails.forEach(detail => { detail.open = true; });
});
window.addEventListener('afterprint', () => {
  closedDetails.forEach(detail => { detail.open = false; });
});
