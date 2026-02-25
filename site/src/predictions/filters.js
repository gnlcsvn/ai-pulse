import { createMultiSelect } from '../shared/multiselect.js'

export function renderFilters(predictions, { onFilter }) {
    const bar = document.getElementById('filter-bar')
    bar.innerHTML = ''

    const categories = [...new Set(predictions.map(p => p.category))].sort()
    const people = [...new Set(predictions.map(p => p.person.name))].sort()

    let selectedCategories = new Set()
    let selectedPeople = new Set()

    const catLabel = document.createElement('label')
    catLabel.textContent = 'Category:'
    bar.appendChild(catLabel)

    createMultiSelect(bar, {
        id: 'filter-category',
        label: 'All categories',
        items: categories,
        onChange(selected) {
            selectedCategories = selected
            onFilter({ categories: selectedCategories, people: selectedPeople })
        },
    })

    const personLabel = document.createElement('label')
    personLabel.textContent = 'Person:'
    bar.appendChild(personLabel)

    createMultiSelect(bar, {
        id: 'filter-person',
        label: 'All people',
        items: people,
        onChange(selected) {
            selectedPeople = selected
            onFilter({ categories: selectedCategories, people: selectedPeople })
        },
    })
}
