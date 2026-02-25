export function renderFilters(predictions, { onFilter }) {
    const bar = document.getElementById('filter-bar')
    const categories = [...new Set(predictions.map(p => p.category))].sort()
    const people = [...new Set(predictions.map(p => p.person.name))].sort()

    let activeCategory = null
    let activePerson = null

    let html = '<label>Category:</label>'
    html += `<button class="filter-btn active" data-type="cat" data-val="">All</button>`
    categories.forEach(c => {
        html += `<button class="filter-btn" data-type="cat" data-val="${c}">${c}</button>`
    })
    html += '<div class="filter-separator"></div><label>Person:</label>'
    html += `<button class="filter-btn active" data-type="person" data-val="">All</button>`
    people.forEach(p => {
        html += `<button class="filter-btn" data-type="person" data-val="${p}">${p}</button>`
    })
    bar.innerHTML = html

    bar.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const type = btn.dataset.type
            const val = btn.dataset.val || null
            if (type === 'cat') {
                activeCategory = val
                bar.querySelectorAll('[data-type="cat"]').forEach(b => b.classList.remove('active'))
            } else {
                activePerson = val
                bar.querySelectorAll('[data-type="person"]').forEach(b => b.classList.remove('active'))
            }
            btn.classList.add('active')
            onFilter({ category: activeCategory, person: activePerson })
        })
    })
}
