#include "tensorflow/core/distributed_runtime/rpc/grpc_schedule_client_impl.h"

namespace tensorflow {

namespace grpc {

	AsyncScheduleClientImpl::AsyncScheduleClientImpl(std::shared_ptr<::grpc::Channel> channel): stub_(ScheduleService::NewStub(channel)), 
                                                            client_id_(-1), 
                                                            num_threads_availables_(1),
                                                            finished_(false) {
		grpc_thread_.reset(new std::thread(std::bind(&AsyncScheduleClientImpl::GrpcThread, this)));
	    stream_ = stub_->AsyncRequestSchedule(&context_, &cq_, reinterpret_cast<void*>(Type::CONNECT));
	 	}
 	void AsyncScheduleClientImpl::AsyncRequestSchedule(int state, std::string type_device, int num_type){
	  /*
      if (state == 2) {
        stream_->WritesDone(reinterpret_cast<void*>(Type::WRITES_DONE));
        return false;
      }
      */

      // Data we are sending to the server.
      ClientRequest request;
      request.set_state(state);
      request.set_type_device(type_device);
      request.set_num_type_device(num_type);

      // This is important: You can have at most one write or at most one read
      // at any given time. The throttling is performed by gRPC completion
      // queue. If you queue more than one write/read, the stream will crash.
      // Because this stream is bidirectional, you *can* have a single read
      // and a single write request queued for the same stream. Writes and reads
      // are independent of each other in terms of ordering/delivery.
      //std::cout << " ** Sending request: " << user << std::endl;
      stream_->Write(request, reinterpret_cast<void*>(Type::WRITE));
      //return true;
    }
    
    void AsyncScheduleClientImpl::AsyncClientRequestNextMessage() {
      //std::cout << " ** Got response: " << response_.message() << std::endl;

      // The tag is the link between our thread (main thread) and the completion
      // queue thread. The tag allows the completion queue to fan off
      // notification handlers for the specified read/write requests as they
      // are being processed by gRPC.
      stream_->Read(&response_, reinterpret_cast<void*>(Type::WRITE));
    }
    

    void AsyncScheduleClientImpl::FinishedRPCCLient(){
    	finished_=true;
    }

}
}