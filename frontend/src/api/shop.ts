import { apiClient } from './client';
import { ShopItem, PurchaseResponse, MintResponse } from './types';

export const fetchShopItems = async (): Promise<ShopItem[]> => {
  const response = await apiClient.get('/api/shop/items');
  return response.data;
};

export const buyShopItem = async (userId: string | number, itemId: number, idempotencyKey: string): Promise<PurchaseResponse> => {
  const response = await apiClient.post('/api/shop/buy', {
    user_id: userId.toString(),
    item_id: itemId,
    idempotency_key: idempotencyKey,
  });
  return response.data;
};

export const mintNft = async (userId: string | number, title: string, idempotencyKey: string): Promise<MintResponse> => {
  const response = await apiClient.post('/api/shop/mint-nft', {
    user_id: userId.toString(),
    title,
    idempotency_key: idempotencyKey,
  });
  return response.data;
};
