/**
 * 行情数据查询页面
 * 股票搜索、K线图、数据表格
 */
import React, { useState, useEffect } from 'react';
import { Row, Col, Card, Form, DatePicker, Select, Button, Checkbox, Space, Alert } from 'antd';
import { StockBasic, DailyKline, KlineQueryParams } from '@/api/types';
import { getDailyKline, getMinuteKline } from '@/api/market';
import { useWebSocketContext } from '@/context/WebSocketContext';
import { KLINE_FREQS } from '@/utils/constants';
import StockSearch from './components/StockSearch';
import KLineChart from './components/KLineChart';
import DataTable from './components/DataTable';
import PriceTicker from '@/components/PriceTicker';
import { RealtimeQuote } from '@/api/types';
import './index.css';
import dayjs from 'dayjs';

const { RangePicker } = DatePicker;

const MarketData: React.FC = () => {
  const [selectedStocks, setSelectedStocks] = useState<StockBasic[]>([]);
  const [currentCode, setCurrentCode] = useState<string>('');
  const [klineData, setKlineData] = useState<DailyKline[]>([]);
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm();
  const { subscribe, unsubscribe, quotes } = useWebSocketContext();

  // 当前选中的实时报价
  const currentQuote: RealtimeQuote | undefined = currentCode
    ? quotes.get(currentCode)
    : undefined;

  // 处理股票选择
  const handleStockSelect = (stock: StockBasic) => {
    const exists = selectedStocks.find((s) => s.code === stock.code);
    if (exists) {
      setSelectedStocks(selectedStocks.filter((s) => s.code !== stock.code));
    } else {
      setSelectedStocks([...selectedStocks, stock]);
    }
  };

  // 切换当前显示的股票
  const handleStockClick = (stock: StockBasic) => {
    setCurrentCode(stock.code);
    // 重新查询数据
    form.submit();
  };

  // 订阅/取消订阅实时行情
  useEffect(() => {
    const codes = selectedStocks.map((s) => s.code);
    subscribe(codes);
    return () => {
      unsubscribe(codes);
    };
  }, [selectedStocks, subscribe, unsubscribe]);

  // 提交查询
  const handleQuery = async (values: any) => {
    if (!currentCode) {
      return;
    }

    setLoading(true);
    try {
      const params: KlineQueryParams = {
        code: currentCode,
        freq: values.freq || '1d',
      };

      if (values.dateRange) {
        params.start_date = dayjs(values.dateRange[0]).format('YYYYMMDD');
        params.end_date = dayjs(values.dateRange[1]).format('YYYYMMDD');
      }

      let data: DailyKline[] = [];
      if (params.freq === '1d') {
        data = await getDailyKline(params);
      } else {
        data = await getMinuteKline(params) as unknown as DailyKline[];
      }

      // 按日期倒序排列
      data.sort((a, b) => {
        const dateA = 'trade_date' in a ? a.trade_date : a.trade_time;
        const dateB = 'trade_date' in b ? b.trade_date : b.trade_time;
        return dateB.localeCompare(dateA);
      });

      setKlineData(data);
    } catch (error) {
      console.error('Query failed:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="market-data-page">
      <h1>行情数据查询</h1>
      <Row gutter={[16, 16]}>
        <Col xs={24} md={8}>
          <Card title="股票搜索" className="search-card">
            <StockSearch
              onSelect={handleStockSelect}
              selectedCodes={selectedStocks.map((s) => s.code)}
            />
            <div className="selected-stocks">
              <p style={{ marginTop: 16 }}>已选股票:</p>
              {selectedStocks.length === 0 ? (
                <div style={{ color: '#999' }}>未选择股票</div>
              ) : (
                selectedStocks.map((stock) => {
                  const quote = quotes.get(stock.code);
                  return (
                    <div
                      key={stock.code}
                      onClick={() => handleStockClick(stock)}
                      className={`stock-item ${
                        currentCode === stock.code ? 'active' : ''
                      }`}
                    >
                      {quote ? (
                        <PriceTicker quote={quote} selected={currentCode === stock.code} />
                      ) : (
                        <Card size="small">{stock.code} - {stock.name}</Card>
                      )}
                    </div>
                  );
                })
              )}
            </div>
          </Card>
        </Col>
        <Col xs={24} md={16}>
          <Card>
            <Form
              form={form}
              layout="inline"
              onFinish={handleQuery}
              initialValues={{ freq: '1d' }}
            >
              <Form.Item label="K线周期" name="freq">
                <Select style={{ width: 120 }} options={KLINE_FREQS} />
              </Form.Item>
              <Form.Item label="日期范围" name="dateRange">
                <RangePicker />
              </Form.Item>
              <Form.Item>
                <Button
                  type="primary"
                  htmlType="submit"
                  disabled={!currentCode}
                  loading={loading}
                >
                  查询
                </Button>
              </Form.Item>
            </Form>
          </Card>

          {!currentCode && (
            <Alert
              message="请选择一只股票"
              description="从左侧选择股票后点击查询按钮"
              type="info"
              style={{ marginTop: 16 }}
            />
          )}

          {currentQuote && (
            <Card title="实时行情" style={{ marginTop: 16 }}>
              <PriceTicker quote={currentQuote} />
            </Card>
          )}

          <Card title="K线图" style={{ marginTop: 16 }}>
            <KLineChart data={klineData} />
          </Card>

          <Card title="数据明细" style={{ marginTop: 16 }}>
            <DataTable data={klineData} loading={loading} />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default MarketData;
