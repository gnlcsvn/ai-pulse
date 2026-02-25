import { escapeHtml } from '../shared/utils.js'

export function renderFilters(predictions, { onFilter }) {
    const bar = document.getElementById('filter-bar')
    const categories = [...new Set(predictions.map(p => p.category))].sort()
    const people = [...new Set(predictions.map(p => p.person.name))].sort()

    bar.innerHTML = `
        <label for="filter-category">Category:</label>
        <select id="filter-category" class="filter-select">
            <option value="">All categories</option>
            ${categories.map(c => `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`).join('')}
        </select>
        <label for="filter-person">Person:</label>
        <select id="filter-person" class="filter-select">
            <option value="">All people</option>
            ${people.map(p => `<option value="${escapeHtml(p)}">${escapeHtml(p)}</option>`).join('')}
        </select>
    `

    const catSelect = document.getElementById('filter-category')
    const personSelect = document.getElementById('filter-person')

    catSelect.addEventListener('change', () => {
        onFilter({ category: catSelect.value || null, person: personSelect.value || null })
    })
    personSelect.addEventListener('change', () => {
        onFilter({ category: catSelect.value || null, person: personSelect.value || null })
    })
}
