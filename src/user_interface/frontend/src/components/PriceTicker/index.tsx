/**
 * 实时价格 Ticker 组件
 * 显示单只股票实时价格和涨跌
 */
import React from 'react';
import { Card, Tag, Typography } from 'antd';
import { RealtimeQuote } from '@/api/types';
import {
  formatPrice,
  formatChangePct,
  getChangeColor,
  formatVolume,
  formatAmount,
} from '@/utils/formatters';
import './index.css';

const { Text } = Typography;

interface PriceTickerProps {
  quote: RealtimeQuote;
  onClick?: () => void;
  selected?: boolean;
}

const PriceTicker: React.FC<PriceTickerProps> = ({
  quote,
  onClick,
  selected = false,
}) => {
  const changeColor = getChangeColor(quote.change_pct);
  const isUp = quote.change_pct > 0;
  const isDown = quote.change_pct < 0;

  return (
    <Card
      className={`price-ticker ${selected ? 'selected' : ''}`}
      size="small"
      onClick={onClick}
      hoverable
    >
      <div className="price-ticker-header">
        <div>
          <Text strong>{quote.code}</Text> <Text type="secondary">{quote.name}</Text>
        </div>
        {isUp && <Tag color="red">涨</Tag>}
        {isDown && <Tag color="green">跌</Tag>}
        {!isUp && !isDown && <Tag>平</Tag>}
      </div>
      <div className="price-ticker-price" style={{ color: changeColor }}>
        {formatPrice(quote.price)}
        <span className="change" style={{ color: changeColor }}>
          {formatChangePct(quote.change_pct)}
        </span>
      </div>
      <div className="price-ticker-footer">
        <span>
          量: {formatVolume(quote.volume)}
        </span>
        <span>
          额: {formatAmount(quote.amount)}
        </span>
      </div>
    </Card>
  );
};

export default PriceTicker;
