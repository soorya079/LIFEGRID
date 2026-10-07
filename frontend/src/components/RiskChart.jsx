import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'

const levels = [['LOW', '#31816b'], ['MEDIUM', '#c39731'], ['HIGH', '#d67835'], ['CRITICAL', '#bd4d40']]

export default function RiskChart({ distribution }) {
  const data = levels.map(([name, color]) => ({ name, value: distribution[name] || 0, color }))
  const total = data.reduce((sum, item) => sum + item.value, 0)
  return (
    <div className="risk-chart-layout">
      <div className="risk-chart-plot" aria-label="Risk distribution donut chart">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart><Pie data={data} dataKey="value" nameKey="name" innerRadius="66%" outerRadius="90%" paddingAngle={3} stroke="none" isAnimationActive={false}>
            {data.map((entry) => <Cell key={entry.name} fill={entry.color} />)}
          </Pie><Tooltip formatter={(value, name) => [`${value} zones`, name]} contentStyle={{ border: '1px solid #dce5e1', borderRadius: 6, fontSize: 12 }} /></PieChart>
        </ResponsiveContainer>
        <div className="risk-chart-center"><strong>{total}</strong><span>ZONES</span></div>
      </div>
      <div className="risk-legend">{data.map((item) => <div className="risk-legend-row" key={item.name}><span className="legend-label"><i style={{ backgroundColor: item.color }} />{item.name}</span><strong>{item.value}</strong></div>)}</div>
    </div>
  )
}