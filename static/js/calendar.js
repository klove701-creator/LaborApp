(function(){
  const calendarEl = document.getElementById('calendar');
  if (!calendarEl) return;

  let current = new Date();
  let projectName = calendarEl.dataset.project || '';
  let datesWithData = new Set(JSON.parse(calendarEl.dataset.dates || '[]'));

  const monthLabel = document.getElementById('calendarMonth');
  const gridEl = document.getElementById('calendarGrid');
  const prevBtn = document.getElementById('prevMonth');
  const nextBtn = document.getElementById('nextMonth');

  function formatDate(year, month, day){
    return `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
  }

  function renderCalendar(year, month){
    if (!gridEl || !monthLabel) return;
    const monthNames = ['January','February','March','April','May','June','July','August','September','October','November','December'];
    monthLabel.textContent = `${monthNames[month]} ${year}`;
    gridEl.innerHTML = '';

    const firstDay = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();

    // prepend blank cells
    for (let i=0; i<firstDay; i++) {
      const blank = document.createElement('div');
      blank.classList.add('empty');
      gridEl.appendChild(blank);
    }

    for (let day=1; day<=daysInMonth; day++) {
      const cell = document.createElement('div');
      cell.textContent = day;
      const key = formatDate(year, month, day);
      if (datesWithData.has(key)) {
        cell.classList.add('has-data');
      }
      gridEl.appendChild(cell);
    }
  }

  async function loadDates(year, month){
    if (!projectName) return;
    const monthStr = `${year}-${String(month + 1).padStart(2,'0')}`;
    try {
      const res = await fetch(`/project/${encodeURIComponent(projectName)}/dates-with-data?month=${monthStr}`);
      if (res.ok) {
        const data = await res.json();
        datesWithData = new Set(data);
      }
    } catch (err) {
      console.error('Failed to load dates', err);
    }
  }

  async function changeMonth(delta){
    current.setMonth(current.getMonth() + delta);
    await loadDates(current.getFullYear(), current.getMonth());
    renderCalendar(current.getFullYear(), current.getMonth());
  }

  prevBtn && prevBtn.addEventListener('click', () => changeMonth(-1));
  nextBtn && nextBtn.addEventListener('click', () => changeMonth(1));

  (async () => {
    await loadDates(current.getFullYear(), current.getMonth());
    renderCalendar(current.getFullYear(), current.getMonth());
  })();
})();
