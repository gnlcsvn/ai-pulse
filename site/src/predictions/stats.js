export function renderStats(predictions) {
    const people = new Set(predictions.map(p => p.person.name))
    const datedCount = predictions.filter(p => p.timeframe.earliest_year && p.timeframe.latest_year).length
    const agiMidpoints = predictions
        .filter(p => p.category === 'AGI timeline' && p.timeframe.midpoint_year)
        .map(p => p.timeframe.midpoint_year)
        .sort((a, b) => a - b)
    const medianAGI = agiMidpoints.length ? agiMidpoints[Math.floor(agiMidpoints.length / 2)] : 'N/A'
    const cats = new Set(predictions.map(p => p.category))

    document.getElementById('stats-grid').innerHTML = `
        <div class="stat-card"><div class="value">${datedCount}</div><div class="label">Dated Predictions</div></div>
        <div class="stat-card"><div class="value">${predictions.length}</div><div class="label">Total (incl. undated)</div></div>
        <div class="stat-card"><div class="value">${people.size}</div><div class="label">People</div></div>
        <div class="stat-card"><div class="value">${agiMidpoints.length}</div><div class="label">AGI Timeline Predictions</div></div>
        <div class="stat-card"><div class="value">${medianAGI}</div><div class="label">Median AGI Year</div></div>
        <div class="stat-card"><div class="value">${cats.size}</div><div class="label">Categories</div></div>
    `
}
