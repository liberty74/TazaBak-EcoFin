import React, { useState } from 'react';
import { ShoppingBag, Star, Zap, Leaf, ShieldCheck, Check, Loader2, Sparkles, Image as ImageIcon } from 'lucide-react';
import { useAuth } from '../store/AuthContext';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { fetchUserDashboard } from '../api/users';
import { fetchShopItems, buyShopItem, mintNft } from '../api/shop';
import { handleApiError, resolveMediaUrl, queryKeys, EcoNFT } from '../api';
import { useLocaleTheme } from '../store/LocaleThemeContext';
import { motion, AnimatePresence } from 'motion/react';
import { toast } from 'sonner';
import EcoNftImage from '../components/common/EcoNftImage';
import { createRequestId } from '../lib/utils';

export const NFT_PRICE_POINTS = 100;

export default function ShopPage() {
  const { user } = useAuth();
  const { t } = useLocaleTheme();
  const [activeTab, setActiveTab] = useState<'shop' | 'mint'>('shop');
  const queryClient = useQueryClient();

  const { data: dashboard } = useQuery({
    queryKey: queryKeys.user.dashboard(user?.id),
    queryFn: () => fetchUserDashboard(user?.id || ''),
    enabled: !!user?.id,
  });

  const { data: items = [], isLoading: itemsLoading } = useQuery({
    queryKey: queryKeys.shop.items,
    queryFn: fetchShopItems,
  });

  const points = dashboard?.profile.points || 0;

  // Shop state
  const [buyingId, setBuyingId] = useState<number | null>(null);

  const handlePurchase = async (itemId: number) => {
    if (!user?.id) return;
    setBuyingId(itemId);
    try {
      const idempotencyKey = createRequestId();
      const res = await buyShopItem(user.id, itemId, idempotencyKey);
      toast.success('Товар успешно приобретен!');
      queryClient.invalidateQueries({ queryKey: queryKeys.user.profile(user.id) });
      queryClient.invalidateQueries({ queryKey: queryKeys.user.dashboard(user.id) });
      queryClient.invalidateQueries({ queryKey: queryKeys.user.transactions(user.id) });
    } catch (e: unknown) {
      const normErr = handleApiError(e);
      toast.error(normErr.message);
    } finally {
      setBuyingId(null);
    }
  };

  // Mint state
  const [mintTitle, setMintTitle] = useState('');
  const [isMinting, setIsMinting] = useState(false);
  const [revealedNft, setRevealedNft] = useState<EcoNFT | null>(null);

  const handleMint = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user?.id || !mintTitle.trim()) return;

    if (points < NFT_PRICE_POINTS) {
      toast.error(t('insufficientPoints') || 'Недостаточно баллов для генерации Eco-NFT.');
      return;
    }

    setIsMinting(true);
    try {
      const idempotencyKey = createRequestId();
      const res = await mintNft(user.id, mintTitle, idempotencyKey);
      setRevealedNft(res.nft);
      toast.success(`NFT успешно создан! Списано баллов: ${res.price_points}. Новый баланс: ${res.current_balance}`);
      
      queryClient.invalidateQueries({ queryKey: queryKeys.user.profile(user.id) });
      queryClient.invalidateQueries({ queryKey: queryKeys.user.dashboard(user.id) });
      queryClient.invalidateQueries({ queryKey: queryKeys.user.transactions(user.id) });
      queryClient.invalidateQueries({ queryKey: queryKeys.user.nfts(user.id) });
      queryClient.invalidateQueries({ queryKey: queryKeys.leaderboard });
    } catch (e: unknown) {
      const normErr = handleApiError(e);
      if (normErr.status === 409) {
        if (normErr.message.toLowerCase().includes('insufficient') || normErr.message.toLowerCase().includes('points') || normErr.message.toLowerCase().includes('балл')) {
          toast.error('Недостаточно баллов для создания Eco-NFT.');
        } else if (normErr.message.toLowerCase().includes('idempotency') || normErr.message.toLowerCase().includes('conflict') || normErr.message.toLowerCase().includes('идемпотент')) {
          toast.error('Конфликт ключа идемпотентности. Пожалуйста, попробуйте изменить название и отправить запрос заново.');
        } else {
          toast.error(normErr.message);
        }
      } else {
        toast.error(normErr.message);
      }
    } finally {
      setIsMinting(false);
      setMintTitle('');
    }
  };

  return (
    <div className="p-4 md:p-8 max-w-5xl mx-auto w-full h-full flex flex-col pt-8 pb-24 lg:pb-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-primary mb-1">Магазин Наград</h1>
          <p className="text-graphite/60">Обменивайте баллы на мерч и создавайте NFT</p>
        </div>
        <div className="bg-white border border-sand px-4 py-2 rounded-2xl flex items-center gap-3 shadow-sm shrink-0">
          <div className="bg-primary/10 p-2 rounded-full text-primary">
            <Leaf className="w-5 h-5" />
          </div>
          <div>
            <p className="text-xs text-graphite/50 font-medium leading-none">Ваш баланс</p>
            <p className="font-bold text-lg leading-none mt-1">{points}</p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-6 bg-cream p-1 rounded-2xl border border-sand/50 w-fit">
        <button 
          onClick={() => setActiveTab('shop')}
          className={`px-6 py-2 rounded-xl font-bold text-sm transition-all cursor-pointer ${activeTab === 'shop' ? 'bg-white shadow-sm text-primary' : 'text-graphite/50 hover:text-graphite'}`}
        >
          Каталог
        </button>
        <button 
          onClick={() => setActiveTab('mint')}
          className={`px-6 py-2 rounded-xl font-bold text-sm transition-all flex gap-2 items-center cursor-pointer ${activeTab === 'mint' ? 'bg-white shadow-sm text-primary' : 'text-graphite/50 hover:text-graphite'}`}
        >
          <Sparkles className="w-4 h-4" />
          Создать NFT
        </button>
      </div>

      {/* Content */}
      {activeTab === 'shop' && (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
          {itemsLoading ? (
            Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="animate-pulse bg-white border border-sand rounded-3xl p-6 h-[300px]" />
            ))
          ) : items.length > 0 ? (
            items.map((item) => (
              <motion.div 
                key={item.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-white border border-sand rounded-3xl p-6 flex flex-col items-center text-center shadow-sm hover:shadow-md transition-shadow relative overflow-hidden"
              >
                {!item.is_active && (
                  <div className="absolute inset-0 bg-white/60 backdrop-blur-[2px] z-10 flex items-center justify-center">
                    <span className="bg-graphite text-white font-bold px-4 py-2 rounded-xl">Нет в наличии</span>
                  </div>
                )}
                
                <div className="w-24 h-24 bg-cream rounded-full flex items-center justify-center mb-4 shadow-inner overflow-hidden">
                  {item.image_url ? (
                    <img src={resolveMediaUrl(item.image_url)!} alt={item.title} className="w-full h-full object-cover" />
                  ) : (
                    <ImageIcon className="w-10 h-10 text-graphite/20" />
                  )}
                </div>
                
                <h3 className="font-bold text-lg mb-1">{item.title}</h3>
                <p className="text-xs text-graphite/50 mb-4">{item.description}</p>
                <div className="mt-auto w-full">
                  <button 
                    onClick={() => handlePurchase(item.id)}
                    disabled={points < item.price_points || buyingId === item.id || !item.is_active}
                    className={`w-full py-3 rounded-xl font-bold flex items-center justify-center gap-2 transition-colors cursor-pointer ${
                      points >= item.price_points && item.is_active
                        ? 'bg-primary text-white hover:bg-primary/90' 
                        : 'bg-sand text-graphite/40 cursor-not-allowed'
                    }`}
                  >
                    {buyingId === item.id ? (
                      <Loader2 className="w-5 h-5 animate-spin" />
                    ) : (
                      <>
                        <span>{item.price_points} баллов</span>
                        <ShoppingBag className="w-4 h-4" />
                      </>
                    )}
                  </button>
                </div>
              </motion.div>
            ))
          ) : (
            <div className="col-span-full py-12 text-center text-graphite/50">
              В магазине пока нет доступных товаров
            </div>
          )}
        </div>
      )}

      {activeTab === 'mint' && (
        <div className="max-w-md mx-auto w-full">
          <div className="bg-white border border-sand rounded-3xl p-6 md:p-8 shadow-sm text-center">
            <div className="w-20 h-20 bg-primary/10 text-primary rounded-full flex items-center justify-center mx-auto mb-6">
              <Sparkles className="w-10 h-10" />
            </div>
            <h2 className="text-2xl font-bold mb-2">{t('generateNftTitle')}</h2>
            <p className="text-graphite/60 mb-8 text-sm leading-relaxed">
              {t('generateNftDesc')}
            </p>
            
            <form onSubmit={handleMint} className="flex flex-col gap-4">
              <div className="text-left">
                <label className="block text-sm font-bold text-graphite mb-2">{t('nftNameLabel')}</label>
                <input 
                  type="text" 
                  value={mintTitle}
                  onChange={e => setMintTitle(e.target.value)}
                  placeholder={t('nftNamePlaceholder')}
                  required
                  maxLength={50}
                  className="w-full bg-cream border border-sand rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-primary/50 text-graphite"
                  disabled={isMinting}
                />
              </div>
              
              <button 
                type="submit"
                disabled={isMinting || points < NFT_PRICE_POINTS || !mintTitle.trim()}
                className="w-full bg-primary text-white py-4 rounded-xl font-bold flex items-center justify-center gap-2 hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed mt-4 cursor-pointer"
              >
                {isMinting ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    <span>{t('mintingLoading')}</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="w-5 h-5" />
                    <span>{t('mintBtn')}</span>
                  </>
                )}
              </button>
            </form>
          </div>
        </div>
      )}

      {/* Reveal Modal */}
      <AnimatePresence>
        {revealedNft && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 bg-black/60 backdrop-blur-sm"
              onClick={() => setRevealedNft(null)}
            />
            <motion.div 
              initial={{ scale: 0.9, opacity: 0, y: 20 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              exit={{ scale: 0.9, opacity: 0, y: 20 }}
              className="relative bg-white rounded-3xl p-8 max-w-sm w-full text-center shadow-2xl z-10"
            >
              <h2 className="text-2xl font-bold text-primary mb-2">{t('nftSuccess')}</h2>
              <p className="text-graphite/60 mb-6 text-sm">{t('nftSuccessDesc')}</p>
              
              <div className="w-full aspect-square bg-cream rounded-2xl mb-6 overflow-hidden flex items-center justify-center border-4 border-sand shadow-inner p-4">
                <EcoNftImage 
                  svgContent={revealedNft.svg_content} 
                  title={revealedNft.title}
                  className="w-full h-full object-contain drop-shadow-md"
                />
              </div>
              
              <h3 className="font-bold text-xl mb-1">{revealedNft.title}</h3>
              <p className="text-xs text-graphite/40 font-mono mb-6">ID: {revealedNft.token_id}</p>
              
              <button 
                onClick={() => setRevealedNft(null)}
                className="w-full bg-primary text-white py-3 rounded-xl font-bold cursor-pointer"
              >
                {t('excellentBtn')}
              </button>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
