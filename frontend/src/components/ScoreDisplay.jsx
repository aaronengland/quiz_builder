export default function ScoreDisplay({ score, total }) {
  const percentage = Math.round((score / total) * 100)

  let grade = 'poor'
  if (percentage >= 80) grade = 'excellent'
  else if (percentage >= 60) grade = 'good'
  else if (percentage >= 40) grade = 'fair'

  return (
    <div className={`score-display score-${grade}`}>
      <div className="score-number">{score}/{total}</div>
      <div className="score-percentage">{percentage}%</div>
      <div className="score-label">
        {grade === 'excellent' && 'Excellent!'}
        {grade === 'good' && 'Good job!'}
        {grade === 'fair' && 'Not bad!'}
        {grade === 'poor' && 'Keep learning!'}
      </div>
    </div>
  )
}
