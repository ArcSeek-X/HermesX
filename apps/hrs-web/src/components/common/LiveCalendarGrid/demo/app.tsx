import dayGridPlugin from '@fullcalendar/react/daygrid'
import timeGridPlugin from '@fullcalendar/react/timegrid'
import listPlugin from '@fullcalendar/react/list'
import multiMonthPlugin from '@fullcalendar/react/multimonth'
import { EventCalendar } from './event-calendar'
import './app.css'

export function App() {
  return (
    <EventCalendar
      plugins={[
        dayGridPlugin,
        timeGridPlugin,
        listPlugin,
        multiMonthPlugin,
      ]}
      addButton={{
        text: 'Add Event',
        click() {
          alert('handle add event...')
        },
      }}
      availableViews={['dayGridMonth', 'timeGridWeek', 'timeGridDay', 'listWeek', 'multiMonthYear']}
      initialView='dayGridMonth'
    />
  )
}
