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

function applyFilters({ category, person }) {
    filteredPredictions = allPredictions.filter(p => {
        if (category && p.category !== category) return false
        if (person && p.person.name !== person) return false
        return true
    })
    renderTimeline(filteredPredictions, allPredictions)
    renderTable(filteredPredictions)
}

loadData()
