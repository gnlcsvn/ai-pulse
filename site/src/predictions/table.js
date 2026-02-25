import { CAT_COLORS, CONFIDENCE_COLORS } from '../shared/colors.js'
import { escapeHtml } from '../shared/utils.js'

let sortCol = 'midpoint'
let sortAsc = true

export function renderTable(predictions) {
    const tbody = document.getElementById('table-body')
    const sorted = [...predictions].sort((a, b) => {
        let va, vb
        switch (sortCol) {
            case 'person': va = a.person.name; vb = b.person.name; break
            case 'prediction': va = a.prediction; vb = b.prediction; break
            case 'category': va = a.category; vb = b.category; break
            case 'timeframe': va = a.timeframe.raw || ''; vb = b.timeframe.raw || ''; break
            case 'midpoint': va = a.timeframe.midpoint_year || 9999; vb = b.timeframe.midpoint_year || 9999; break
            case 'confidence': va = a.confidence.level; vb = b.confidence.level; break
            case 'made': va = a.source.prediction_date || a.source.upload_date; vb = b.source.prediction_date || b.source.upload_date; break
            case 'source': va = a.source.upload_date; vb = b.source.upload_date; break
            default: va = a.timeframe.midpoint_year || 9999; vb = b.timeframe.midpoint_year || 9999
        }
        if (typeof va === 'string') return sortAsc ? va.localeCompare(vb) : vb.localeCompare(va)
        return sortAsc ? va - vb : vb - va
    })

    tbody.innerHTML = sorted.map(p => {
        const cat = p.category
        const color = CAT_COLORS[cat] || CAT_COLORS.other
        const confColor = CONFIDENCE_COLORS[p.confidence.level] || '#9e9a92'
        const confText = p.confidence.percentage
            ? `${p.confidence.percentage}%`
            : p.confidence.level
        const year = p.timeframe.midpoint_year || '-'
        return `<tr>
            <td><strong style="color:#131314">${escapeHtml(p.person.name)}</strong><br><span style="color:#8a857d;font-size:0.68rem">${escapeHtml(p.person.company)}</span></td>
            <td style="max-width:300px;color:#131314">${escapeHtml(p.prediction)}</td>
            <td><span class="cat-badge" style="background:${color}18;color:${color};border:1px solid ${color}30">${escapeHtml(cat)}</span></td>
            <td style="font-size:0.72rem;color:#8a857d;max-width:180px">${p.timeframe.raw ? escapeHtml(p.timeframe.raw) : '<em style="color:#c4c0b8">no timeframe</em>'}</td>
            <td style="text-align:center;font-weight:600;color:#c4704e">${year}</td>
            <td><span style="color:${confColor};font-weight:500">${escapeHtml(confText)}</span></td>
            <td style="font-size:0.72rem;color:#8a857d;white-space:nowrap">${p.source.prediction_date || p.source.upload_date}</td>
            <td><a href="${escapeHtml(p.source.timestamp_url)}" target="_blank" title="${escapeHtml(p.source.title)}">&#9654; ${p.source.timestamp_display}</a></td>
        </tr>`
    }).join('')

    // Update sort arrows
    document.querySelectorAll('#predictions-table th').forEach(th => {
        const arrow = th.querySelector('.sort-arrow')
        if (th.dataset.sort === sortCol) {
            arrow.textContent = sortAsc ? ' \u25B2' : ' \u25BC'
        } else {
            arrow.textContent = ''
        }
    })
}

export function initSortHandlers(onSort) {
    document.querySelectorAll('#predictions-table th').forEach(th => {
        th.addEventListener('click', () => {
            const col = th.dataset.sort
            if (sortCol === col) { sortAsc = !sortAsc }
            else { sortCol = col; sortAsc = true }
            onSort()
        })
    })
}
