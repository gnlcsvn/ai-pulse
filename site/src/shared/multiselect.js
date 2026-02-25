import { escapeHtml } from './utils.js'

/**
 * Creates a multi-select dropdown with checkboxes.
 *
 * @param {HTMLElement} container - Parent element to mount into
 * @param {Object} options
 * @param {string} options.id - Unique ID for this dropdown
 * @param {string} options.label - Label text (e.g. "All categories")
 * @param {string[]} options.items - List of selectable values
 * @param {(selected: Set) => void} options.onChange - Called with the set of selected values
 */
export function createMultiSelect(container, { id, label, items, onChange }) {
    const wrapper = document.createElement('div')
    wrapper.className = 'multiselect'
    wrapper.id = id

    const selected = new Set()

    const trigger = document.createElement('button')
    trigger.className = 'multiselect-trigger'
    trigger.type = 'button'

    const dropdown = document.createElement('div')
    dropdown.className = 'multiselect-dropdown'

    function updateLabel() {
        if (selected.size === 0) {
            trigger.innerHTML = `${escapeHtml(label)} <span class="multiselect-arrow"></span>`
        } else if (selected.size === 1) {
            trigger.innerHTML = `${escapeHtml([...selected][0])} <span class="multiselect-arrow"></span>`
        } else {
            trigger.innerHTML = `${selected.size} selected <span class="multiselect-arrow"></span>`
        }
    }

    // Clear button
    const clearBtn = document.createElement('button')
    clearBtn.className = 'multiselect-clear'
    clearBtn.type = 'button'
    clearBtn.textContent = 'Clear'
    clearBtn.addEventListener('click', (e) => {
        e.stopPropagation()
        selected.clear()
        dropdown.querySelectorAll('input').forEach(cb => cb.checked = false)
        updateLabel()
        onChange(selected)
    })
    dropdown.appendChild(clearBtn)

    // Checkbox items
    items.forEach(item => {
        const row = document.createElement('label')
        row.className = 'multiselect-item'

        const checkbox = document.createElement('input')
        checkbox.type = 'checkbox'
        checkbox.value = item

        checkbox.addEventListener('change', () => {
            if (checkbox.checked) {
                selected.add(item)
            } else {
                selected.delete(item)
            }
            updateLabel()
            onChange(selected)
        })

        const text = document.createElement('span')
        text.textContent = item

        row.appendChild(checkbox)
        row.appendChild(text)
        dropdown.appendChild(row)
    })

    // Toggle dropdown
    trigger.addEventListener('click', () => {
        const isOpen = wrapper.classList.contains('open')
        // Close all other dropdowns first
        document.querySelectorAll('.multiselect.open').forEach(el => el.classList.remove('open'))
        if (!isOpen) wrapper.classList.add('open')
    })

    // Close on click outside
    document.addEventListener('click', (e) => {
        if (!wrapper.contains(e.target)) {
            wrapper.classList.remove('open')
        }
    })

    updateLabel()
    wrapper.appendChild(trigger)
    wrapper.appendChild(dropdown)
    container.appendChild(wrapper)

    return { selected }
}
