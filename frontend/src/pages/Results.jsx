import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import ScoreDisplay from '../components/ScoreDisplay'

const OPTIONS = ['A', 'B', 'C', 'D']

export default function Results() {
  const { id } = useParams()
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    // Try sessionStorage first (set during quiz submission)
    const cached = sessionStorage.getItem(`quiz-result-${id}`)
    if (cached) {
      setResult(JSON.parse(cached))
      setLoading(false)
      return
    }

    // Fallback: quiz hasn't been submitted yet
    setError('Results not available. Please take the quiz first.')
    setLoading(false)
  }, [id])

  if (loading) return <div className="loading-state"><div className="spinner" /></div>
  if (error) return (
    <div className="results-page">
      <p className="error-message">{error}</p>
      <Link to={`/quiz/${id}`} className="btn btn-primary" style={{ marginTop: '1rem' }}>Take Quiz</Link>
    </div>
  )
  if (!result) return null

  return (
    <div className="results-page">
      <h2>Quiz Results</h2>

      <ScoreDisplay score={result.score} total={result.total} />

      <div className="results-list">
        {result.questions.map((q, i) => {
          const userAnswer = result.user_answers[String(q.id)]
          const isCorrect = userAnswer === q.correct_answer

          return (
            <div key={q.id} className={`result-card ${isCorrect ? 'correct' : 'incorrect'}`}>
              <h3 className="question-number">Question {i + 1}</h3>
              <p className="question-text">{q.question_text}</p>

              <div className="options-review">
                {OPTIONS.map((letter) => {
                  const optionKey = `option_${letter.toLowerCase()}`
                  const isUserAnswer = userAnswer === letter
                  const isCorrectAnswer = q.correct_answer === letter

                  let className = 'option-review'
                  if (isCorrectAnswer) className += ' correct-answer'
                  if (isUserAnswer && !isCorrect) className += ' wrong-answer'

                  return (
                    <div key={letter} className={className}>
                      <span className="option-letter">{letter}</span>
                      <span className="option-text">{q[optionKey]}</span>
                      {isCorrectAnswer && <span className="badge badge-correct">Correct</span>}
                      {isUserAnswer && !isCorrect && <span className="badge badge-wrong">Your answer</span>}
                    </div>
                  )
                })}
              </div>

              {q.explanation && (
                <div className="explanation">
                  <strong>Explanation:</strong> {q.explanation}
                </div>
              )}
            </div>
          )
        })}
      </div>

      <div className="results-actions">
        <Link to="/" className="btn btn-primary">New Quiz</Link>
        <Link to="/history" className="btn btn-secondary">View History</Link>
      </div>
    </div>
  )
}
