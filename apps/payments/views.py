from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Payment
from .serializers import PaymentSerializer, CheckoutSerializer


class CheckoutView(APIView):
    def post(self, request):
        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        # Create payment record (mock - in production integrate with Stripe)
        payment = Payment.objects.create(
            user=request.user,
            amount=data['amount'],
            description=data['description'],
            status='completed'  # Mock success
        )
        
        # Upgrade user to pro
        request.user.is_pro = True
        request.user.save()
        
        return Response({
            'payment': PaymentSerializer(payment).data,
            'message': 'Payment successful'
        }, status=status.HTTP_201_CREATED)


class PaymentWebhookView(APIView):
    permission_classes = []  # No auth for webhooks
    
    def post(self, request):
        # Handle Stripe webhook (mock implementation)
        return Response({'received': True})


class PaymentHistoryView(generics.ListAPIView):
    serializer_class = PaymentSerializer

    def get_queryset(self):
        return Payment.objects.filter(user=self.request.user)
