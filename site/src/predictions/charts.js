import * as d3 from 'd3'
import { CAT_COLORS } from '../shared/colors.js'

export function renderCategoryChart(predictions) {
    const container = document.getElementById('category-chart')
    const counts = {}
    predictions.forEach(p => { counts[p.category] = (counts[p.category] || 0) + 1 })
    const data = Object.entries(counts).sort((a, b) => b[1] - a[1])

    const w = container.clientWidth || 400
    const h = 280
    const radius = Math.min(w, h) / 2 - 20

    const svg = d3.select(container).append('svg').attr('width', w).attr('height', h)
    const g = svg.append('g').attr('transform', `translate(${w / 3},${h / 2})`)

    const pie = d3.pie().value(d => d[1]).sort(null)
    const arc = d3.arc().innerRadius(radius * 0.55).outerRadius(radius)

    g.selectAll('path')
        .data(pie(data)).enter()
        .append('path')
        .attr('d', arc)
        .attr('fill', d => CAT_COLORS[d.data[0]] || '#9e9a92')
        .attr('stroke', '#f5f4f0')
        .attr('stroke-width', 2)

    // Legend
    const legend = svg.append('g').attr('transform', `translate(${w * 0.62}, 20)`)
    data.forEach((d, i) => {
        const row = legend.append('g').attr('transform', `translate(0, ${i * 22})`)
        row.append('rect').attr('width', 10).attr('height', 10)
            .attr('fill', CAT_COLORS[d[0]] || '#9e9a92')
        row.append('text').attr('x', 16).attr('y', 9)
            .attr('fill', '#5c5850').attr('font-size', '10px')
            .text(`${d[0]} (${d[1]})`)
    })
}

export function renderPersonChart(predictions) {
    const container = document.getElementById('person-chart')
    const counts = {}
    predictions.forEach(p => { counts[p.person.name] = (counts[p.person.name] || 0) + 1 })
    const data = Object.entries(counts).sort((a, b) => b[1] - a[1])

    const w = container.clientWidth || 400
    const h = 280
    const margin = { top: 10, right: 20, bottom: 30, left: 140 }

    const svg = d3.select(container).append('svg').attr('width', w).attr('height', h)

    const x = d3.scaleLinear()
        .domain([0, d3.max(data, d => d[1])])
        .range([margin.left, w - margin.right])

    const y = d3.scaleBand()
        .domain(data.map(d => d[0]))
        .range([margin.top, h - margin.bottom])
        .padding(0.25)

    svg.selectAll('rect')
        .data(data).enter()
        .append('rect')
        .attr('x', margin.left)
        .attr('y', d => y(d[0]))
        .attr('width', d => x(d[1]) - margin.left)
        .attr('height', y.bandwidth())
        .attr('fill', '#c4704e')
        .attr('opacity', 0.65)

    svg.selectAll('.bar-label')
        .data(data).enter()
        .append('text')
        .attr('x', margin.left - 5)
        .attr('y', d => y(d[0]) + y.bandwidth() / 2)
        .attr('text-anchor', 'end')
        .attr('dominant-baseline', 'middle')
        .attr('fill', '#5c5850')
        .attr('font-size', '10px')
        .attr('font-weight', '500')
        .text(d => d[0])

    svg.selectAll('.bar-count')
        .data(data).enter()
        .append('text')
        .attr('x', d => x(d[1]) + 5)
        .attr('y', d => y(d[0]) + y.bandwidth() / 2)
        .attr('dominant-baseline', 'middle')
        .attr('fill', '#8a857d')
        .attr('font-size', '10px')
        .text(d => d[1])
}
