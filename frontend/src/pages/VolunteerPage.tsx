import { useEffect, useMemo, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { CheckCircle2, ChevronRight, Clock, HeartHandshake, Loader2, MapPin, RefreshCw } from 'lucide-react';
import { toast } from 'sonner';
import { fetchVolunteerTasks, handleApiError, queryKeys, registerForTask } from '../api';
import { useAuth } from '../store/AuthContext';

const storageKey = (username: string) => `registeredTaskIds:${username}`;

export default function VolunteerPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [registeringId, setRegisteringId] = useState<number | null>(null);
  const [registeredIds, setRegisteredIds] = useState<number[]>([]);

  useEffect(() => {
    if (!user) return;
    try {
      const parsed: unknown = JSON.parse(localStorage.getItem(storageKey(user.username)) ?? '[]');
      setRegisteredIds(Array.isArray(parsed) ? parsed.filter((id): id is number => Number.isInteger(id)) : []);
    } catch {
      setRegisteredIds([]);
    }
  }, [user]);

  useEffect(() => {
    if (user) localStorage.setItem(storageKey(user.username), JSON.stringify(registeredIds));
  }, [registeredIds, user]);

  const tasksQuery = useQuery({
    queryKey: queryKeys.volunteer.tasks(false),
    queryFn: () => fetchVolunteerTasks(false),
  });

  const tasks = tasksQuery.data ?? [];
  const available = useMemo(() => tasks.filter((task) => !registeredIds.includes(task.id)), [tasks, registeredIds]);
  const participating = useMemo(() => tasks.filter((task) => registeredIds.includes(task.id)), [tasks, registeredIds]);

  const handleRegister = async (taskId: number) => {
    if (!user) return;
    if (user.role !== 'volunteer') {
      toast.info('Для участия войдите в демонстрационном режиме как волонтёр.');
      return;
    }
    setRegisteringId(taskId);
    try {
      const result = await registerForTask(taskId, user.id);
      setRegisteredIds((current) => current.includes(taskId) ? current : [...current, taskId]);
      toast.success(`Вы зарегистрированы. Награда ${result.reward_points_pending} баллов будет начислена диспетчером после выполнения.`);
      await queryClient.invalidateQueries({ queryKey: queryKeys.volunteer.tasks(false) });
    } catch (error: unknown) {
      const normalized = handleApiError(error);
      if (normalized.status === 409) {
        setRegisteredIds((current) => current.includes(taskId) ? current : [...current, taskId]);
        toast.info('Вы уже зарегистрированы на это задание.');
      } else {
        toast.error(normalized.message);
      }
    } finally {
      setRegisteringId(null);
    }
  };

  return (
    <div className="p-4 md:p-8 max-w-4xl mx-auto w-full pt-8 pb-24 lg:pb-8 text-foreground">
      <section className="bg-primary/10 border border-primary/20 rounded-3xl p-6 mb-8 relative overflow-hidden">
        <HeartHandshake className="absolute -right-8 -bottom-10 w-44 h-44 text-primary/10" aria-hidden="true" />
        <div className="relative">
          <div className="flex items-center gap-3 mb-2">
            <HeartHandshake className="w-8 h-8 text-primary" />
            <h1 className="text-2xl font-bold">Волонтёрский центр</h1>
          </div>
          <p className="text-muted-foreground max-w-xl">Участвуйте в добрых делах. Баллы начисляются только после подтверждения выполнения диспетчером.</p>
        </div>
      </section>

      {tasksQuery.isPending ? (
        <div className="space-y-4" aria-label="Загрузка заданий">
          {[1, 2, 3].map((id) => <div key={id} className="h-36 rounded-2xl bg-card border border-border animate-pulse" />)}
        </div>
      ) : tasksQuery.isError ? (
        <div className="bg-card border border-critical/30 rounded-3xl p-8 text-center">
          <p className="text-critical font-bold mb-4">Не удалось загрузить задания.</p>
          <button onClick={() => tasksQuery.refetch()} className="inline-flex items-center gap-2 bg-primary text-white px-5 py-3 rounded-xl font-bold min-h-11">
            <RefreshCw className="w-4 h-4" /> Повторить
          </button>
        </div>
      ) : (
        <div className="space-y-8">
          {participating.length > 0 && (
            <section>
              <h2 className="text-xl font-bold mb-4">Вы участвуете</h2>
              <div className="space-y-4">
                {participating.map((task) => <TaskCard key={task.id} task={task} registered />)}
              </div>
            </section>
          )}

          <section>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold">Доступные задания</h2>
              <span className="bg-muted text-muted-foreground px-3 py-1 rounded-full text-xs font-bold">{available.length}</span>
            </div>
            {available.length === 0 ? (
              <div className="bg-card border border-border rounded-3xl p-8 text-center text-muted-foreground">Новых заданий пока нет.</div>
            ) : (
              <div className="space-y-4">
                {available.map((task) => (
                  <TaskCard
                    key={task.id}
                    task={task}
                    action={
                      <button
                        onClick={() => handleRegister(task.id)}
                        disabled={registeringId === task.id || user?.role !== 'volunteer'}
                        className="bg-primary text-white px-5 py-2.5 rounded-xl font-bold text-sm inline-flex items-center gap-2 disabled:opacity-50 min-h-11"
                      >
                        {registeringId === task.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <ChevronRight className="w-4 h-4" />}
                        {user?.role === 'volunteer' ? 'Участвовать' : 'Доступно волонтёрам'}
                      </button>
                    }
                  />
                ))}
              </div>
            )}
          </section>
        </div>
      )}
    </div>
  );
}

function TaskCard({ task, registered = false, action }: {
  task: { id: number; title: string; description: string; reward_points: number; date: string; time: string };
  registered?: boolean;
  action?: React.ReactNode;
}) {
  return (
    <article className="bg-card border border-border rounded-2xl p-5 shadow-sm">
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
        <div>
          <h3 className="font-bold text-lg">{task.title}</h3>
          <p className="text-muted-foreground text-sm mt-2">{task.description}</p>
        </div>
        <span className="bg-primary/10 text-primary px-3 py-1 rounded-lg font-bold text-sm shrink-0">+{task.reward_points} баллов</span>
      </div>
      <div className="flex flex-wrap gap-4 text-sm text-muted-foreground mt-4">
        <span className="inline-flex items-center gap-2"><MapPin className="w-4 h-4" /> Кокшетау</span>
        <span className="inline-flex items-center gap-2"><Clock className="w-4 h-4" /> {task.date}, {task.time}</span>
      </div>
      <div className="border-t border-border mt-4 pt-4 flex justify-end">
        {registered ? <span className="inline-flex items-center gap-2 text-primary font-bold text-sm"><CheckCircle2 className="w-5 h-5" /> Вы зарегистрированы</span> : action}
      </div>
    </article>
  );
}
