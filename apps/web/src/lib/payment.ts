import * as PortOne from '@portone/browser-sdk/v2';

export interface PaymentRequest {
	storeId: string;
	channelKey: string;
	paymentId: string;
	orderName: string;
	totalAmount: number;
	currency?: string;
	payMethod?: string;
}

export interface PaymentResult {
	paymentId: string;
	success: boolean;
	errorCode?: string;
	errorMessage?: string;
}

export async function requestPayment(req: PaymentRequest): Promise<PaymentResult> {
	// PortOne's request type is a discriminated union per payMethod; we currently
	// only fire CARD payments, so we shape the call as that variant explicitly.
	const response = await PortOne.requestPayment({
		storeId: req.storeId,
		channelKey: req.channelKey,
		paymentId: req.paymentId,
		orderName: req.orderName,
		totalAmount: req.totalAmount,
		currency: (req.currency ?? 'KRW') as 'KRW',
		payMethod: 'CARD'
	} as Parameters<typeof PortOne.requestPayment>[0]);

	if (response?.code) {
		return {
			paymentId: req.paymentId,
			success: false,
			errorCode: response.code,
			errorMessage: response.message
		};
	}

	return { paymentId: req.paymentId, success: true };
}
