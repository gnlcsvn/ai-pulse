import * as d3 from 'd3'
import { CAT_COLORS } from '../shared/colors.js'
import { escapeHtml } from '../shared/utils.js'

export function renderTimeline(filteredPredictions, allPredictions) {
    const container = document.getElementById('timeline')
    container.innerHTML = ''

    const data = filteredPredictions.filter(p => p.timeframe.earliest_year && p.timeframe.latest_year)
    if (!data.length) {
        container.innerHTML = '<p style="color:var(--color-text-muted);padding:2rem;text-align:center">No predictions with year ranges to display</p>'
        return
    }

    // Group by person
    const byPerson = {}
    data.forEach(p => {
        if (!byPerson[p.person.name]) byPerson[p.person.name] = { name: p.person.name, company: p.person.company, preds: [] }
        byPerson[p.person.name].preds.push(p)
    })
    const people = Object.values(byPerson).sort((a, b) => b.preds.length - a.preds.length)

    const margin = { top: 40, right: 30, bottom: 40, left: 200 }
    const rowH = 28
    const width = Math.max(container.clientWidth - 20, 800)
    const height = margin.top + margin.bottom + people.length * rowH * 1.5 + 20

    const svg = d3.select(container).append('svg')
        .attr('width', width).attr('height', height)
        .attr('class', 'timeline-svg')

    // X scale
    const minYear = 2026
    const maxYear = 2055
    const x = d3.scaleLinear()
        .domain([minYear, maxYear])
        .range([margin.left, width - margin.right])

    // Y scale
    const y = d3.scaleBand()
        .domain(people.map(p => p.name))
        .range([margin.top, height - margin.bottom])
        .padding(0.3)

    // Grid lines
    const years = d3.range(minYear, maxYear + 1, 2)
    svg.selectAll('.grid-line')
        .data(years).enter()
        .append('line')
        .attr('x1', d => x(d)).attr('x2', d => x(d))
        .attr('y1', margin.top - 10).attr('y2', height - margin.bottom)
        .attr('stroke', '#e2dfd8').attr('stroke-dasharray', '2,6')

    // AGI consensus band
    const agiPreds = allPredictions.filter(p => p.category === 'AGI timeline' && p.timeframe.midpoint_year)
    if (agiPreds.length >= 3) {
        const mids = agiPreds.map(p => p.timeframe.midpoint_year).sort((a, b) => a - b)
        const q1 = mids[Math.floor(mids.length * 0.25)]
        const q3 = mids[Math.floor(mids.length * 0.75)]
        const median = mids[Math.floor(mids.length / 2)]

        svg.append('rect')
            .attr('x', x(q1)).attr('width', x(q3) - x(q1))
            .attr('y', margin.top - 10).attr('height', height - margin.top - margin.bottom + 10)
            .attr('fill', 'rgba(201, 126, 110, 0.08)')

        svg.append('line')
            .attr('x1', x(median)).attr('x2', x(median))
            .attr('y1', margin.top - 10).attr('y2', height - margin.bottom)
            .attr('stroke', '#c97e6e').attr('stroke-width', 1).attr('stroke-dasharray', '6,4')
            .attr('opacity', 0.45)

        svg.append('text')
            .attr('x', x(median)).attr('y', margin.top - 15)
            .attr('text-anchor', 'middle').attr('fill', '#c97e6e')
            .attr('font-size', '9px').attr('opacity', 0.7)
            .attr('font-weight', '500').attr('letter-spacing', '0.05em')
            .text(`AGI MEDIAN: ${median}`)
    }

    // X axis
    svg.append('g')
        .attr('transform', `translate(0,${height - margin.bottom})`)
        .call(d3.axisBottom(x).tickValues(years).tickFormat(d3.format('d')))
        .selectAll('text').attr('fill', '#8a857d').attr('font-size', '10px')
    svg.selectAll('.domain').attr('stroke', '#c4c0b8')
    svg.selectAll('.tick line').attr('stroke', '#c4c0b8')

    // Y axis labels
    svg.selectAll('.y-label')
        .data(people).enter()
        .append('text')
        .attr('x', margin.left - 10)
        .attr('y', d => y(d.name) + y.bandwidth() / 2)
        .attr('text-anchor', 'end')
        .attr('dominant-baseline', 'middle')
        .attr('fill', '#131314')
        .attr('font-size', '11px')
        .attr('font-weight', '500')
        .text(d => d.name)

    svg.selectAll('.y-company')
        .data(people).enter()
        .append('text')
        .attr('x', margin.left - 10)
        .attr('y', d => y(d.name) + y.bandwidth() / 2 + 13)
        .attr('text-anchor', 'end')
        .attr('dominant-baseline', 'middle')
        .attr('fill', '#8a857d')
        .attr('font-size', '9px')
        .text(d => d.company)

    // Prediction bars + dots
    const tooltip = d3.select('#tooltip')

    data.forEach(p => {
        const yPos = y(p.person.name) + y.bandwidth() / 2
        const e = Math.max(p.timeframe.earliest_year, minYear)
        const l = Math.min(p.timeframe.latest_year, maxYear)
        const cat = p.category
        const color = CAT_COLORS[cat] || CAT_COLORS.other

        // Range bar
        if (e !== l) {
            svg.append('line')
                .attr('x1', x(e)).attr('x2', x(l))
                .attr('y1', yPos).attr('y2', yPos)
                .attr('stroke', color).attr('stroke-width', 2.5)
                .attr('opacity', 0.35)
                .attr('stroke-linecap', 'round')
        }

        // Midpoint dot
        const mid = p.timeframe.midpoint_year || ((e + l) / 2)
        const dot = svg.append('circle')
            .attr('cx', x(Math.min(Math.max(mid, minYear), maxYear)))
            .attr('cy', yPos)
            .attr('r', 4.5)
            .attr('fill', color)
            .attr('stroke', '#faf9f6')
            .attr('stroke-width', 1.5)
            .attr('cursor', 'pointer')
            .attr('opacity', 0.85)

        dot.on('mouseover', (event) => {
            dot.attr('r', 6.5).attr('opacity', 1)
            const confStr = p.confidence.percentage
                ? `${p.confidence.percentage}% (${p.confidence.level})`
                : p.confidence.level
            const madeDate = p.source.prediction_date || p.source.upload_date
            tooltip.html(`
                <div class="tt-prediction">${escapeHtml(p.prediction)}</div>
                <div class="tt-meta">
                    <span>${escapeHtml(p.person.name)}</span> — ${escapeHtml(p.person.role)}, ${escapeHtml(p.person.company)}<br>
                    Timeframe: <span>${escapeHtml(p.timeframe.raw || '\u2014')}</span><br>
                    Confidence: <span>${escapeHtml(confStr)}</span><br>
                    Category: <span>${escapeHtml(p.category)}</span><br>
                    Made: <span>${madeDate}</span>
                </div>
                <span class="tt-link">Click to watch source &#8599;</span>
            `)
            tooltip.style('opacity', 1)
                .style('left', (event.pageX + 15) + 'px')
                .style('top', (event.pageY - 10) + 'px')
        })
        .on('mouseout', () => {
            dot.attr('r', 4.5).attr('opacity', 0.85)
            tooltip.style('opacity', 0)
        })
        .on('click', () => {
            window.open(p.source.timestamp_url, '_blank')
        })
    })
}
