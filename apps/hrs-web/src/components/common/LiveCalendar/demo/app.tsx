/**
 * @file app.tsx
 * @description FullCalendar 官方示例的本地 demo 入口（参考代码，不参与正式构建），
 * 用于本地调式 EventCalendar 主题效果，正式实现见 ../LiveCalendar.tsx。
 * @author Lensgcx (GaoCangxiong)
 */
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
