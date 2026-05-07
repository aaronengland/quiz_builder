import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import QuestionCard from '../components/QuestionCard'

export default function Quiz() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [quiz, setQuiz] = useState(null)
  const [answers, setAnswers] = useState({})
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetch(`/api/quiz/${id}`)
      .then((resp) => {
        if (!resp.ok) throw new Error('Quiz not found')
        return resp.json()
      })
      .then(setQuiz)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [id])

  const handleSelect = (questionId, letter) => {
    setAnswers((prev) => ({ ...prev, [questionId]: letter }))
  }

  const allAnswered = quiz && Object.keys(answers).length === quiz.questions.length

  const handleSubmit = async () => {
    if (!allAnswered) return

    setSubmitting(true)
    try {
      const resp = await fetch(`/api/quiz/${id}/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ answers }),
      })

      if (!resp.ok) throw new Error('Failed to submit quiz')

      const result = await resp.json()
      sessionStorage.setItem(`quiz-result-${id}`, JSON.stringify(result))
      navigate(`/results/${id}`)
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) return <div className="loading-state"><div className="spinner" /></div>
  if (error) return <p className="error-message">{error}</p>
  if (!quiz) return null

  return (
    <div className="quiz-page">
      <div className="quiz-header">
        <h2>{quiz.topic}</h2>
        <p className="quiz-progress">
          {Object.keys(answers).length} of {quiz.questions.length} answered
        </p>
      </div>

      {quiz.questions.map((q, i) => (
        <QuestionCard
          key={q.id}
          question={q}
          index={i}
          selectedAnswer={answers[q.id]}
          onSelect={(letter) => handleSelect(q.id, letter)}
        />
      ))}

      <div className="submit-section">
        <button
          className="btn btn-primary btn-lg"
          onClick={handleSubmit}
          disabled={!allAnswered || submitting}
        >
          {submitting ? 'Submitting...' : 'Submit Quiz'}
        </button>
        {!allAnswered && (
          <p className="hint">Answer all questions to submit.</p>
        )}
      </div>
    </div>
  )
}
