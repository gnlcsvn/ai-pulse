import '../shared/styles.css'
import './styles.css'
import { renderStats } from './stats.js'
import { renderFilters } from './filters.js'
import { renderTimeline } from './timeline.js'
import { renderCategoryChart, renderPersonChart } from './charts.js'
import { renderTable, initSortHandlers } from './table.js'

let allPredictions = []
let filteredPredictions = []

async function loadData() {
    const response = await fetch(`${import.meta.env.BASE_URL}data/predictions.json`)
    allPredictions = await response.json()
    filteredPredictions = [...allPredictions]
    init()
}

function init() {
    renderStats(allPredictions)
    renderFilters(allPredictions, { onFilter: applyFilters })
    renderTimeline(filteredPredictions, allPredictions)
    renderCategoryChart(allPredictions)
    renderPersonChart(allPredictions)
    renderTable(filteredPredictions)
    initSortHandlers(() => renderTable(filteredPredictions))
}

function applyFilters({ categories, people }) {
    filteredPredictions = allPredictions.filter(p => {
        if (categories.size && !categories.has(p.category)) return false
        if (people.size && !people.has(p.person.name)) return false
        return true
    })
    renderTimeline(filteredPredictions, allPredictions)
    renderTable(filteredPredictions)
}

loadData()
