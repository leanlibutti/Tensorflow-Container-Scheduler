//#include "tensorflow/core/distributed_runtime/rpc/grpc_schedule_client.h"

#include <memory>
#include <thread>
#include "grpcpp/grpcpp.h"
#include "tensorflow/core/protobuf/schedule_service.pb.h"
#include "tensorflow/core/protobuf/schedule_service.grpc.pb.h"

namespace tensorflow {

namespace grpc {

class AsyncScheduleClientImpl {

  enum class Type {
    CONNECT = 1,
    UPDATE = 2,
    WRITE = 3,
    FINISH = 4
  };
  public:
    AsyncScheduleClientImpl(std::shared_ptr<::grpc::Channel> channel);

    // Similar to the async hello example in greeter_async_client but does not
    // wait for the response. Instead queues up a tag in the completion queue
    // that is notified when the server responds back (or when the stream is
    // closed). Returns false when the stream is requested to be closed.
    //Call from Executor
    void AsyncRequestSchedule(int state, std::string type_device, int num_type);

    void FinishedRPCCLient();

    void AsyncClientRequestNextMessage();

    ~AsyncScheduleClientImpl() {
      std::cout << "Shutting down client...." << std::endl;
      ::grpc::Status status;
      cq_.Shutdown();
      grpc_thread_->join();
    }

  private:

  	// Context for the client. It could be used to convey extra information to
    // the server and/or tweak certain RPC behaviors.
    ::grpc::ClientContext context_;

    // The producer-consumer queue we use to communicate asynchronously with the
    // gRPC runtime.
    ::grpc::CompletionQueue cq_;

    // Out of the passed in Channel comes the stub, stored here, our view of the
    // server's exposed services.
    std::unique_ptr<ScheduleService::Stub> stub_;

    // The bidirectional, asynchronous stream for sending/receiving messages.
    std::unique_ptr<::grpc::ClientAsyncReaderWriter<ClientRequest, ServerReply>> stream_;

    ClientRequest request_;

    // Allocated protobuf that holds the response. In real clients and servers,
    // the memory management would a bit more complex as the thread that fills
    // in the response should take care of concurrency as well as memory
    // management.
    ServerReply response_;

    // Thread that notifies the gRPC completion queue tags.
    std::unique_ptr<std::thread> grpc_thread_;

    // Finish status when the client is done with the stream.
    ::grpc::Status finish_status_ = ::grpc::Status::OK;

    //Available threads to use
    int num_threads_availables_;

    int client_id_;

    bool finished_;

    // Runs a gRPC completion-queue processing thread. Checks for 'Next' tag
    // and processes them until there are no more (or when the completion queue
    // is shutdown).
    void GrpcThread() {
      while (true) {
        void* got_tag;
        bool ok = false;
        // Block until the next result is available in the completion queue "cq".
        // The return value of Next should always be checked. This return value
        // tells us whether there is any kind of event or the cq_ is shutting
        // down.
        if (!cq_.Next(&got_tag, &ok)) {
          std::cerr << "Client stream closed. Quitting" << std::endl;
          break;
        }

        // It's important to process all tags even if the ok is false. One might
        // want to deallocate memory that has be reinterpret_cast'ed to void*
        // when the tag got initialized. For our example, we cast an int to a
        // void*, so we don't have extra memory management to take care of.
        if ((ok) && (!finished_)) {
        
          std::cout << std::endl
                    << "**** Processing completion queue tag " << got_tag
                    << std::endl;
          switch (static_cast<Type>(reinterpret_cast<long>(got_tag))) {
            case Type::WRITE:
              std::cout << "Update num threads." << std::endl;
              AsyncClientRequestNextMessage();
              num_threads_availables_= response_.num_threads();
              if (client_id_ == -1) client_id_= response_.client_id();
              break;
            default:
              std::cerr << "Unexpected tag " << got_tag << std::endl;
              GPR_ASSERT(false);
          }
        
     	}

     	if(finished_)
       		stream_->Write(request_, reinterpret_cast<void*>(Type::FINISH));
      }
    }
};

/*
void NewScheduleClient(AsyncScheduleClient** schedule_client, std::shared_ptr<::grpc::Channel> channel) {
	AsyncScheduleClientImpl* impl= new AsyncScheduleClientImpl(channel);
	*schedule_client = impl;
}
*/

}
}