import { useState } from 'react';

export default function QuestionForm() {
  const [equipment, setEquipment] = useState('Centrifugal pump');
  const [problem, setProblem] = useState('Discharge pressure is low.');
  const [answer, setAnswer] = useState('');

  async function submit(event) {
    event.preventDefault();
    const response = await fetch('/api/troubleshoot', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({equipment, problem}),
    });
    const result = await response.json();
    setAnswer(result.answer);
  }

  return <form onSubmit={submit}>
    <label>Equipment<input value={equipment} onChange={(event) => setEquipment(event.target.value)} /></label>
    <label>Problem<textarea value={problem} onChange={(event) => setProblem(event.target.value)} /></label>
    <button type="submit">Ask PlantOps AI</button>
    {answer && <p>{answer}</p>}
  </form>;
}
