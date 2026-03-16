/**
 * 股票搜索组件
 */
import React, { useState } from 'react';
import { Input, Button, List, Tag, Space } from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import { StockBasic } from '@/api/types';
import { searchStocks } from '@/api/market';

interface StockSearchProps {
  onSelect: (stock: StockBasic) => void;
  selectedCodes: string[];
}

const StockSearch: React.FC<StockSearchProps> = ({ onSelect, selectedCodes }) => {
  const [keyword, setKeyword] = useState('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<StockBasic[]>([]);

  const handleSearch = async () => {
    if (!keyword.trim()) {
      return;
    }
    setLoading(true);
    try {
      const response = await searchStocks({ keyword: keyword.trim(), limit: 20 });
      setResults(response.items);
    } catch (error) {
      console.error('Search failed:', error);
    } finally {
      setLoading(false);
    }
  };

  const isSelected = (code: string) => selectedCodes.includes(code);

  return (
    <div>
      <Space.Compact style={{ width: '100%' }}>
        <Input
          placeholder="输入股票代码或名称..."
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          onPressEnter={handleSearch}
        />
        <Button
          type="primary"
          icon={<SearchOutlined />}
          onClick={handleSearch}
          loading={loading}
        >
          搜索
        </Button>
      </Space.Compact>
      {results.length > 0 && (
        <List
          style={{ marginTop: 16, maxHeight: 300, overflow: 'auto' }}
          size="small"
          bordered
          dataSource={results}
          renderItem={(stock) => (
            <List.Item
              onClick={() => onSelect(stock)}
              style={{
                cursor: 'pointer',
                backgroundColor: isSelected(stock.code) ? '#f0f0f0' : undefined,
              }}
            >
              <Space>
                <strong>{stock.code}</strong>
                <span>{stock.name}</span>
                {isSelected(stock.code) && (
                  <Tag color="blue">已选</Tag>
                )}
              </Space>
            </List.Item>
          )}
        />
      )}
    </div>
  );
};

export default StockSearch;
