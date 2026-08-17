import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { CheckCircle2, Loader2, RefreshCw, Users } from 'lucide-react';
import { toast } from 'sonner';
import { completeTask, fetchVolunteerTasks, handleApiError, queryKeys } from '../../api';
import { useAuth } from '../../store/AuthContext';

export default function VolunteerTasksPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [selectedTaskId, setSelectedTaskId] = useState<number | null>(null);
  const [volunteerId, setVolunteerId] = useState('volunteer-1');
  const [submitting, setSubmitting] = useState(false);
  const tasksQuery = useQuery({ queryKey: queryKeys.volunteer.tasks(true), queryFn: () => fetchVolunteerTasks(true) });

  const submit = async () => {
    if (!selectedTaskId || !user || !volunteerId.trim()) return;
    setSubmitting(true);
    try {
      const result = await completeTask(selectedTaskId, volunteerId.trim(), user.id);
      toast.success(`Задание завершено. Начислено ${result.points_awarded} баллов.`);
      setSelectedTaskId(null);
      await queryClient.invalidateQueries({ queryKey: queryKeys.volunteer.tasks(true) });
    } catch (error: unknown) {
      toast.error(handleApiError(error).message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6 pb-24 lg:pb-8 text-foreground">
      <div><h1 className="text-2xl font-bold flex items-center gap-2"><Users className="w-6 h-6 text-primary" /> Волонтёрские задания</h1><p className="text-muted-foreground text-sm mt-1">Подтверждение выполнения и начисление наград.</p></div>
      {tasksQuery.isPending ? <div className="h-48 bg-card border border-border rounded-3xl animate-pulse" /> : tasksQuery.isError ? (
        <button onClick={() => tasksQuery.refetch()} className="bg-primary text-white px-5 py-3 rounded-xl inline-flex items-center gap-2"><RefreshCw className="w-4 h-4" /> Повторить</button>
      ) : (
        <div className="grid gap-4">
          {(tasksQuery.data ?? []).map((task) => (
            <article key={task.id} className="bg-card border border-border rounded-2xl p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div><h2 className="font-bold">{task.title}</h2><p className="text-muted-foreground text-sm mt-1">{task.description}</p><p className="text-xs mt-2">{task.date}, {task.time} · {task.reward_points} баллов</p></div>
              {task.status === 'completed' ? <span className="text-primary font-bold inline-flex items-center gap-2"><CheckCircle2 className="w-5 h-5" /> Завершено</span> : <button onClick={() => setSelectedTaskId(task.id)} className="bg-primary text-white px-4 py-2.5 rounded-xl font-bold shrink-0">Завершить</button>}
            </article>
          ))}
        </div>
      )}
      {selectedTaskId && (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4" role="dialog" aria-modal="true" aria-labelledby="complete-task-title">
          <div className="bg-card border border-border rounded-3xl p-6 max-w-md w-full">
            <h2 id="complete-task-title" className="text-xl font-bold">Подтвердить выполнение</h2>
            <p className="text-muted-foreground text-sm mt-2">Введите username зарегистрированного волонтёра.</p>
            <label className="block text-sm font-bold mt-5" htmlFor="volunteer-id">Username волонтёра</label>
            <input id="volunteer-id" value={volunteerId} onChange={(event) => setVolunteerId(event.target.value)} className="w-full bg-muted border border-border rounded-xl px-4 py-3 mt-2" />
            <div className="grid grid-cols-2 gap-3 mt-6">
              <button onClick={() => setSelectedTaskId(null)} disabled={submitting} className="border border-border rounded-xl py-3 font-bold">Отмена</button>
              <button onClick={submit} disabled={submitting || !volunteerId.trim()} className="bg-primary text-white rounded-xl py-3 font-bold inline-flex items-center justify-center gap-2 disabled:opacity-50">{submitting && <Loader2 className="w-4 h-4 animate-spin" />} Начислить</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
